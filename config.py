import os
from typing import List
from pydantic import BaseSettings

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application settings
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_debug: bool = False
    
    # API settings
    api_title: str = "EventsDC Document Ingestion POC"
    api_version: str = "1.0.0"
    api_rate_limit: int = 100
    
    # File upload settings
    max_file_size_mb: int = 50
    supported_extensions: List[str] = [".pdf", ".docx", ".pptx", ".txt"]
    
    # Document processing settings
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_search_results: int = 50
    
    # OpenAI settings (optional)
    openai_api_key: str = ""
    
    # Security settings
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Logging settings
    log_level: str = "INFO"
    log_file: str = "app.log"
    
    # Data storage paths
    documents_file: str = "search_documents.json"
    embeddings_file: str = "document_embeddings.json"
    processed_docs_file: str = "processed_documents.json"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()