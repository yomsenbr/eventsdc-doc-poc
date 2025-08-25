from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
import numpy as np
import re

from .indexing import get_chroma_collection, fetch_all_docs


def _tokenize(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())


def _safe_norm(arr: np.ndarray) -> np.ndarray:
    """
    Normalize array values to 0..1 safely.
    Works on both NumPy <2.0 and >=2.0.
    """
    if arr.size == 0:
        return arr
    rng = float(np.ptp(arr))  # use np.ptp instead of arr.ptp (NumPy 2.0 safe)
    if rng == 0.0:
        return np.zeros_like(arr, dtype=float)
    return (arr - float(arr.min())) / rng


def keyword_search(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """
    BM25 keyword search over all documents.
    """
    data = fetch_all_docs()
    corpus = data["docs"]
    if not corpus:
        return []
    tokenized_corpus = [_tokenize(d) for d in corpus]
    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(_tokenize(query))
    top_idx = np.argsort(scores)[::-1][:k]
    results = []
    for i in top_idx:
        results.append({
            "id": data["ids"][i],
            "document": corpus[i],
            "metadata": data["metas"][i],
            "score": float(scores[i]),
        })
    return results


def vector_search(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """
    Vector similarity search from ChromaDB.
    """
    coll = get_chroma_collection()
    q = coll.query(
        query_texts=[query],
        n_results=k,
        include=["documents", "metadatas", "distances"]
    )
    results = []
    if q and q.get("ids"):
        for i in range(len(q["ids"][0])):
            results.append({
                "id": q["ids"][0][i],
                "document": q["documents"][0][i],
                "metadata": q["metadatas"][0][i],
                "distance": float(q["distances"][0][i]),
            })
    return results


def hybrid_search(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """
    Combine BM25 keyword scores + vector similarity into one ranking.
    """
    kw = keyword_search(query, k=k * 2)
    vs = vector_search(query, k=k * 2)

    pool: Dict[str, Dict[str, Any]] = {}

    # Normalize BM25 scores (higher is better)
    if kw:
        kw_scores = np.array([r["score"] for r in kw], dtype=float)
        kw_norm = _safe_norm(kw_scores)
        for i, r in enumerate(kw):
            pool[r["id"]] = {"result": r, "kw": float(kw_norm[i]), "vs": 0.0}

    # Normalize vector distances (lower is better → invert)
    if vs:
        vs_dists = np.array([r["distance"] for r in vs], dtype=float)
        vs_norm = 1.0 - _safe_norm(vs_dists)
        for i, r in enumerate(vs):
            if r["id"] in pool:
                pool[r["id"]]["vs"] = float(vs_norm[i])
            else:
                pool[r["id"]] = {"result": r, "kw": 0.0, "vs": float(vs_norm[i])}

    # Blend scores (equal weights here)
    for v in pool.values():
        v["blend"] = 0.5 * v["kw"] + 0.5 * v["vs"]

    merged = sorted(pool.values(), key=lambda x: x["blend"], reverse=True)[:k]

    final: List[Dict[str, Any]] = []
    for m in merged:
        r = m["result"]
        meta = r.get("metadata", {}) or {}
        excerpt = r.get("document") or ""
        final.append({
            "id": r["id"],
            "excerpt": excerpt[:700],
            "filename": meta.get("filename"),
            "doc_id": meta.get("doc_id"),
            "chunk_index": meta.get("chunk_index"),
            "source_path": meta.get("source_path"),
            "score_blend": m["blend"],
        })
    return final
