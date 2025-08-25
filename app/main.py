import os
import uuid
import traceback
import logging
from typing import Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .utils import ALLOWED_EXTS
from .ingestion import (
    save_upload, extract_text_from_pdf, extract_text_from_docx,
    extract_text_from_pptx, extract_text_from_txt
)
from .indexing import upsert_document
from .search import keyword_search, vector_search, hybrid_search

# ---------- Logging ----------
logging.basicConfig(
    filename="server.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

app = FastAPI(title="EventsDC Document POC", version="0.3.0")

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

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

# ---------- Routes ----------
@app.get("/")
def root() -> Dict[str, Any]:
    return {"message": "POC running. Use /docs for UI."}

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
async def ingest(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Save upload -> extract text (OCR for PDFs if needed) -> chunk+embed to Chroma.
    Always returns a dict (never None).
    """
    try:
        ext = _ext(file.filename)
        if ext not in ALLOWED_EXTS:
            raise HTTPException(status_code=400, detail=f"Only {sorted(ALLOWED_EXTS)} supported.")

        raw = await file.read()
        if not raw:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        saved_path = save_upload(file.filename, raw)
        text = _extract_text_by_ext(ext, raw)

        if not text or len(text.strip()) < 5:
            raise HTTPException(status_code=422, detail="No extractable text found (file may be empty or image-only).")

        doc_id = str(uuid.uuid4())
        idx_info = upsert_document(doc_id=doc_id, filename=file.filename, text=text, source_path=saved_path)

        return {
            "message": "Ingested",
            "doc_id": doc_id,
            "filename": file.filename,
            "chunks": idx_info.get("chunks", 0),
            "saved_path": saved_path
        }

    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        logging.exception("Ingest failed")
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
    - Runs hybrid search
    - Composes an answer from top excerpts
    - Returns citations (filename, doc_id, chunk_index, source_path)
    """
    hits = hybrid_search(q, k=k)
    if not hits:
        return {
            "query": q,
            "answer": "I couldn't find enough information in the ingested documents to answer that.",
            "citations": []
        }

    snippets = [h["excerpt"] for h in hits if h.get("excerpt")]
    composed = " ".join(s[:500] for s in snippets)[:1200]
    answer = composed if len(composed.strip()) >= 50 else \
        "I found related passages but not enough detail to answer confidently."
    citations = [{
        "filename": h["filename"],
        "doc_id": h["doc_id"],
        "chunk_index": h["chunk_index"],
        "source_path": h["source_path"]
    } for h in hits]
    return {"query": q, "answer": answer, "citations": citations}

@app.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True}

@app.get("/stats")
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
        logging.exception("Stats failed")
        return {"collection": "docs", "total_chunks": 0, "error": str(e)}
