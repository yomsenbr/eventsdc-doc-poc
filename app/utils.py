import os
from dotenv import load_dotenv

load_dotenv()

CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", "./chroma_db")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

ALLOWED_EXTS = {".pdf", ".docx", ".pptx", ".txt"}
