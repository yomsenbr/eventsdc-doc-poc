import re
import time
from typing import List, Dict, Any
import chromadb
from chromadb.utils import embedding_functions
from .utils import CHROMA_DB_DIR, EMBEDDING_MODEL


def split_into_chunks(text: str, target_words: int = 1000, overlap_words: int = 100) -> List[str]:
    # Simple word-based chunking (~800–1200 tokens for MiniLM)
    words = re.findall(r"\S+", text)
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + target_words, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start = end - overlap_words
        if start < 0:
            start = 0
    return chunks


def get_chroma_collection(name: str = "docs"):
    client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    return client.get_or_create_collection(name=name, embedding_function=ef)


def upsert_document(doc_id: str, filename: str, text: str, source_path: str) -> Dict[str, Any]:
    coll = get_chroma_collection()
    chunks = split_into_chunks(text)
    ids = [f"{doc_id}::chunk::{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "doc_id": doc_id,
            "filename": filename,
            "chunk_index": i,
            "source_path": source_path,
            "ingested_at": int(time.time())
        }
        for i in range(len(chunks))
    ]
    coll.upsert(ids=ids, documents=chunks, metadatas=metadatas)
    return {"doc_id": doc_id, "chunks": len(chunks)}


def fetch_all_docs() -> Dict[str, List[str]]:
    """Return {'ids': [...], 'docs': [...], 'metas': [...]} for building BM25."""
    coll = get_chroma_collection()
    all_ids, all_docs, all_metas = [], [], []
    cursor = 0
    page = 1000
    while True:
        batch = coll.get(include=["documents", "metadatas"], limit=page, offset=cursor)
        ids = batch.get("ids", [])
        if not ids:
            break
        all_ids.extend(ids)
        all_docs.extend(batch.get("documents", []))
        all_metas.extend(batch.get("metadatas", []))
        cursor += len(ids)
    return {"ids": all_ids, "docs": all_docs, "metas": all_metas}
