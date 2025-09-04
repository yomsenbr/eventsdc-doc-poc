import os
import uuid
import traceback
import logging
import re
from typing import Dict, Any
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .config import settings, get_cors_config, get_logging_config
from .security import security_manager, get_security_headers, check_rate_limit
from .monitoring import metrics_collector, security_monitor, health_checker, monitor_request
from .utils import ALLOWED_EXTS
from .ingestion import (
    save_upload, extract_text_from_pdf, extract_text_from_docx,
    extract_text_from_pptx, extract_text_from_txt
)
from .indexing import upsert_document
from .search import keyword_search, vector_search, hybrid_search

# ---------- Logging Setup ----------
logging_config = get_logging_config()
logging.config.dictConfig(logging_config)
logger = logging.getLogger(__name__)

# ---------- Application Setup ----------
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None
)

# ---------- Security Middleware ----------
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.eventsdc.com"]
)

# ---------- CORS ----------
cors_config = get_cors_config()
app.add_middleware(
    CORSMiddleware,
    **cors_config
)

# ---------- Security Headers Middleware ----------
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    for header, value in get_security_headers().items():
        response.headers[header] = value
    return response

# ---------- Request Logging Middleware ----------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.utcnow()
    client_ip = request.client.host if request.client else "unknown"
    
    # Check rate limiting
    await check_rate_limit(client_ip)
    
    response = await call_next(request)
    
    # Log security events
    if response.status_code >= 400:
        security_monitor.log_security_event(
            "HTTP_ERROR",
            {
                "status_code": response.status_code,
                "method": request.method,
                "path": str(request.url.path),
                "user_agent": request.headers.get("user-agent", "unknown")
            },
            client_ip
        )
    
    return response

# ---------- Helpers ----------
def _ext(name: str) -> str:
    return os.path.splitext(name)[1].lower()

def _extract_text_by_ext(ext: str, raw: bytes) -> str:
    if ext == ".pdf":
        return extract_text_from_pdf(raw)
    if ext == ".docx":
        return extract_text_from_docx(raw)
    if ext == ".pptx":
        return extract_text_from_pptx(raw)
    if ext == ".txt":
        return extract_text_from_txt(raw)
    raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

# ---------- Authentication Routes ----------
@app.post("/auth/login")
async def login(username: str, password: str, request: Request) -> Dict[str, Any]:
    """Authenticate user and return access token"""
    client_ip = request.client.host if request.client else "unknown"
    
    # Simple authentication (replace with proper user database)
    if username == "admin" and password == "admin123":  # Change in production!
        access_token = security_manager.create_access_token({"sub": username, "is_admin": True})
        refresh_token = security_manager.create_refresh_token({"sub": username})
        
        logger.info(f"Successful login for user: {username} from IP: {client_ip}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60
        }
    else:
        security_monitor.log_security_event(
            "LOGIN_FAILED",
            {"username": username, "attempted_at": datetime.utcnow().isoformat()},
            client_ip
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/auth/refresh")
async def refresh_token(refresh_token: str) -> Dict[str, Any]:
    """Refresh access token using refresh token"""
    try:
        payload = security_manager.verify_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        access_token = security_manager.create_access_token({"sub": payload["sub"]})
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

# ---------- Public Routes ----------
@app.get("/")
def root() -> Dict[str, Any]:
    return {
        "message": f"{settings.app_name} v{settings.app_version}",
        "environment": settings.environment,
        "status": "running"
    }

@app.post("/upload")
async def upload(file: UploadFile = File(...)) -> Dict[str, Any]:
    ext = _ext(file.filename)
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail=f"Only {sorted(ALLOWED_EXTS)} supported.")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    saved_path = save_upload(file.filename, raw)
    return {"saved_path": saved_path, "size_bytes": len(raw)}

@app.post("/ingest")
@monitor_request("/ingest", "POST")
async def ingest(file: UploadFile = File(...), request: Request = None) -> Dict[str, Any]:
    """
    Save upload -> extract text (OCR for PDFs if needed) -> chunk+embed to Chroma.
    Always returns a dict (never None).
    """
    try:
        # Security validation
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        raw = await file.read()
        if not raw:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        
        # Validate file upload
        validation = security_manager.validate_file_upload(
            file.filename, len(raw), file.content_type or ""
        )
        
        if not validation["valid"]:
            security_monitor.log_security_event(
                "INVALID_FILE_UPLOAD",
                {"filename": file.filename, "errors": validation["errors"]},
                request.client.host if request and request.client else "unknown"
            )
            raise HTTPException(status_code=400, detail=f"File validation failed: {', '.join(validation['errors'])}")
        
        # Use sanitized filename
        safe_filename = validation["sanitized_filename"]
        
        ext = _ext(safe_filename)
        if ext not in ALLOWED_EXTS:
            raise HTTPException(status_code=400, detail=f"Only {sorted(ALLOWED_EXTS)} supported.")

        saved_path = save_upload(safe_filename, raw)
        text = _extract_text_by_ext(ext, raw)

        if not text or len(text.strip()) < 5:
            raise HTTPException(status_code=422, detail="No extractable text found (file may be empty or image-only).")

        doc_id = str(uuid.uuid4())
        idx_info = upsert_document(doc_id=doc_id, filename=safe_filename, text=text, source_path=saved_path)

        # Record metrics
        metrics_collector.record_file_upload(safe_filename, len(raw), True)
        
        logger.info(f"Successfully ingested file: {safe_filename} (doc_id: {doc_id})")

        return {
            "message": "Ingested",
            "doc_id": doc_id,
            "filename": safe_filename,
            "chunks": idx_info.get("chunks", 0),
            "saved_path": saved_path
        }

    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        logger.exception("Ingest failed")
        metrics_collector.record_file_upload(file.filename or "unknown", 0, False)
        return {"message": "Ingest failed", "error": str(e), "trace": tb[:2000]}

@app.get("/search/keyword")
def search_keyword(q: str = Query(..., min_length=1), k: int = 5) -> Dict[str, Any]:
    return {"query": q, "results": keyword_search(q, k=k)}

@app.get("/search/vector")
def search_vector(q: str = Query(..., min_length=1), k: int = 5) -> Dict[str, Any]:
    return {"query": q, "results": vector_search(q, k=k)}

@app.get("/search/hybrid")
def search_hybrid(q: str = Query(..., min_length=1), k: int = 5) -> Dict[str, Any]:
    return {"query": q, "results": hybrid_search(q, k=k)}

@app.get("/chat")
def chat(q: str = Query(..., min_length=1), k: int = 5) -> Dict[str, Any]:
    """
    Lightweight chat:
    - Hybrid search
    - Summarize top excerpts into 2–4 concise sentences
    - Return citations for traceability
    """
    hits = hybrid_search(q, k=k)
    if not hits:
        return {
            "query": q,
            "answer": "I couldn't find enough information in the ingested documents to answer that.",
            "citations": []
        }

    # Gather candidate sentences from top excerpts
    raw = " ".join([h.get("excerpt") or "" for h in hits])
    parts = [s.strip() for s in re.split(r'(?<=[.!?])\s+', raw) if len(s.strip()) > 0]

    # Deduplicate while keeping order
    seen = set()
    unique = []
    for s in parts:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            unique.append(s)

    # Keep the most informative first 2–4 sentences (short and readable)
    summary = " ".join(unique[:4])
    if len(summary) < 80 and len(unique) >= 5:
        summary = " ".join(unique[:5])
    if len(summary) < 40:
        summary = unique[0] if unique else "I found related passages but not enough detail to answer confidently."

    citations = [{
        "filename": h["filename"],
        "doc_id": h["doc_id"],
        "chunk_index": h["chunk_index"],
        "source_path": h["source_path"]
    } for h in hits]

    return {"query": q, "answer": summary, "citations": citations}


@app.get("/stats")
@monitor_request("/stats", "GET")
def stats() -> Dict[str, Any]:
    """
    Return simple count of chunks in the 'docs' collection.
    """
    from .indexing import get_chroma_collection
    try:
        coll = get_chroma_collection()
        total = coll.count() if hasattr(coll, "count") else 0
        return {"collection": "docs", "total_chunks": int(total)}
    except Exception as e:
        logger.exception("Stats failed")
        return {"collection": "docs", "total_chunks": 0, "error": str(e)}

# ---------- Monitoring Endpoints ----------
@app.get("/metrics")
@monitor_request("/metrics", "GET")
def get_metrics() -> Dict[str, Any]:
    """Get application metrics"""
    return metrics_collector.get_metrics_summary()

@app.get("/health")
def health() -> Dict[str, Any]:
    """Get application health status"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "EventsDC Document POC is running"
    }

@app.get("/security/events")
@monitor_request("/security/events", "GET")
def get_security_events() -> Dict[str, Any]:
    """Get security events summary (admin only)"""
    return security_monitor.get_security_summary()

# ---------- Admin Endpoints ----------
@app.post("/admin/reset")
@monitor_request("/admin/reset", "POST")
def admin_reset():
    """
    Delete the local Chroma index and recreate the directory for a clean demo.
    You will need to re-ingest documents after this.
    """
    import shutil
    from .utils import CHROMA_DB_DIR
    try:
        shutil.rmtree(CHROMA_DB_DIR, ignore_errors=True)
        os.makedirs(CHROMA_DB_DIR, exist_ok=True)
        
        # Reset metrics
        metrics_collector.reset_metrics()
        
        logger.info("Database reset completed")
        return {"message": "index reset", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.exception("Admin reset failed")
        raise HTTPException(status_code=500, detail=f"Reset failed: {e}")

@app.post("/admin/clear-logs")
@monitor_request("/admin/clear-logs", "POST")
def clear_logs():
    """Clear application logs (admin only)"""
    try:
        # Clear log files
        log_files = ["logs/app.log", "server.log"]
        for log_file in log_files:
            if os.path.exists(log_file):
                with open(log_file, 'w') as f:
                    f.write("")
        
        # Clear security events
        security_monitor.security_events.clear()
        security_monitor.failed_logins.clear()
        security_monitor.suspicious_ips.clear()
        
        logger.info("Logs cleared")
        return {"message": "logs cleared", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.exception("Clear logs failed")
        raise HTTPException(status_code=500, detail=f"Clear logs failed: {e}")

# ---------- Error Handlers ----------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

