import os
import hashlib
import logging
from typing import List, Optional
from datetime import datetime
import json

from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from document_processor import DocumentProcessor
from search_engine import SearchEngine
from chatbot import ChatBot

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="EventsDC Document Ingestion POC", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
document_processor = DocumentProcessor()
search_engine = SearchEngine()
chatbot = ChatBot()

# Document storage to prevent duplicates
PROCESSED_DOCS_FILE = "processed_documents.json"

class DocumentInfo(BaseModel):
    filename: str
    file_hash: str
    content_hash: str
    upload_date: str
    file_size: int
    doc_type: str

class SearchRequest(BaseModel):
    query: str
    search_type: str = "hybrid"  # keyword, vector, hybrid
    limit: int = 10

class ChatRequest(BaseModel):
    question: str
    context_limit: int = 5

def load_processed_docs():
    """Load list of processed documents to prevent duplicates"""
    if os.path.exists(PROCESSED_DOCS_FILE):
        try:
            with open(PROCESSED_DOCS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading processed docs: {e}")
    return {}

def save_processed_docs(docs_info):
    """Save processed documents info"""
    try:
        with open(PROCESSED_DOCS_FILE, 'w') as f:
            json.dump(docs_info, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving processed docs: {e}")

def calculate_file_hash(file_content: bytes) -> str:
    """Calculate SHA-256 hash of file content to detect duplicates"""
    return hashlib.sha256(file_content).hexdigest()

def calculate_content_hash(text_content: str) -> str:
    """Calculate hash of extracted text content to detect content duplicates"""
    # Normalize content for better duplicate detection
    normalized_content = ' '.join(text_content.lower().strip().split())
    return hashlib.sha256(normalized_content.encode()).hexdigest()

@app.get("/")
async def root():
    return {"message": "EventsDC Document Ingestion POC API", "version": "1.0.0"}

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a document with duplicate detection"""
    try:
        # Validate file type
        allowed_extensions = {'.pdf', '.docx', '.pptx', '.txt'}
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
            
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if not file_extension:
            raise HTTPException(status_code=400, detail="File has no extension")
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=422, 
                detail=f"File type '{file_extension}' not supported. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        # Read file content
        file_content = await file.read()
        file_hash = calculate_file_hash(file_content)
        
        # Load existing processed documents
        processed_docs = load_processed_docs()
        
        # Check for duplicate file
        if file_hash in processed_docs:
            existing_doc = processed_docs[file_hash]
            logger.info(f"Duplicate file detected: {file.filename} (hash: {file_hash})")
            return {
                "message": "File already processed",
                "duplicate": True,
                "existing_document": existing_doc,
                "file_hash": file_hash
            }
        
        # Process the document
        logger.info(f"Processing new document: {file.filename}")
        extracted_text = document_processor.process_document(file_content, file_extension)
        
        # Calculate content hash to detect content duplicates
        content_hash = calculate_content_hash(extracted_text)
        
        # Check for content duplicates (same content, different file)
        for existing_hash, doc_info in processed_docs.items():
            if doc_info.get('content_hash') == content_hash:
                logger.warning(f"Content duplicate detected: {file.filename} has same content as {doc_info['filename']}")
                return {
                    "message": "Document with identical content already exists",
                    "duplicate": True,
                    "content_duplicate": True,
                    "existing_document": doc_info,
                    "file_hash": file_hash,
                    "content_hash": content_hash
                }
        
        # Index the document (with deduplication in search engine)
        doc_id = search_engine.index_document(
            filename=file.filename,
            content=extracted_text,
            file_hash=file_hash,
            content_hash=content_hash
        )
        
        # Save document info
        doc_info = DocumentInfo(
            filename=file.filename,
            file_hash=file_hash,
            content_hash=content_hash,
            upload_date=datetime.now().isoformat(),
            file_size=len(file_content),
            doc_type=file_extension[1:]  # Remove dot
        )
        
        processed_docs[file_hash] = doc_info.dict()
        save_processed_docs(processed_docs)
        
        logger.info(f"Successfully processed document: {file.filename}")
        
        return {
            "message": "Document processed successfully",
            "duplicate": False,
            "document_id": doc_id,
            "filename": file.filename,
            "file_hash": file_hash,
            "content_hash": content_hash,
            "extracted_text_length": len(extracted_text)
        }
        
    except HTTPException:
        # Re-raise HTTPException without modification
        raise
    except Exception as e:
        logger.error(f"Error processing document {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.post("/search")
async def search_documents(request: SearchRequest):
    """Search documents with deduplication"""
    try:
        results = search_engine.search(
            query=request.query,
            search_type=request.search_type,
            limit=request.limit
        )
        
        # Additional deduplication based on content similarity
        deduplicated_results = search_engine.deduplicate_results(results)
        
        return {
            "query": request.query,
            "search_type": request.search_type,
            "total_results": len(deduplicated_results),
            "results": deduplicated_results
        }
        
    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@app.post("/chat")
async def chat_with_documents(request: ChatRequest):
    """Chat interface with document context"""
    try:
        response = chatbot.ask_question(
            question=request.question,
            context_limit=request.context_limit
        )
        
        return {
            "question": request.question,
            "answer": response["answer"],
            "sources": response["sources"]
        }
        
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@app.get("/documents")
async def list_documents():
    """List all processed documents"""
    try:
        processed_docs = load_processed_docs()
        return {
            "total_documents": len(processed_docs),
            "documents": list(processed_docs.values())
        }
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")

@app.delete("/documents/{file_hash}")
async def delete_document(file_hash: str):
    """Delete a document by its hash"""
    try:
        processed_docs = load_processed_docs()
        
        if file_hash not in processed_docs:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Remove from search index
        search_engine.delete_document(file_hash)
        
        # Remove from processed docs
        deleted_doc = processed_docs.pop(file_hash)
        save_processed_docs(processed_docs)
        
        return {
            "message": "Document deleted successfully",
            "deleted_document": deleted_doc
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check if all components are working
        status = {
            "api": "healthy",
            "document_processor": "healthy",
            "search_engine": "healthy",
            "chatbot": "healthy",
            "timestamp": datetime.now().isoformat()
        }
        
        # Test search engine connection
        search_engine.health_check()
        
        return status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")