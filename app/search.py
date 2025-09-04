from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
import numpy as np
import re

from .indexing import get_chroma_collection, fetch_all_docs


def _tokenize(text: str) -> List[str]:
    return re.findall(r"\w+", (text or "").lower())


def _safe_norm(arr: np.ndarray) -> np.ndarray:
    """
    Normalize to 0..1 safely (NumPy 2.0 compatible).
    Returns zeros if the array is constant or empty.
    """
    if arr.size == 0:
        return arr.astype(float)
    rng = float(np.ptp(arr))  # np.ptp works in NumPy 2.0+
    if rng == 0.0:
        return np.zeros_like(arr, dtype=float)
    return (arr - float(arr.min())) / rng


def _excerpt(doc: str, query: str, width: int = 280) -> str:
    text = doc or ""
    q = (query or "").strip().lower()
    if not text:
        return ""
    if not q:
        return text[:width]
    idx = text.lower().find(q)
    if idx == -1:
        return text[:width]
    start = max(0, idx - width // 2)
    end = min(len(text), idx + len(q) + width // 2)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "… " + snippet
    if end < len(text):
        snippet = snippet + " …"
    return snippet


def keyword_search(query: str, k: int = 5) -> List[Dict[str, Any]]:
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
        doc = corpus[i]
        meta = data["metas"][i]
        results.append({
            "id": data["ids"][i],
            "document": doc,                         # keep full text for debugging
            "excerpt": _excerpt(doc, query),         # short snippet for UI
            "metadata": meta,
            "score": float(scores[i]),
        })
    return results


def vector_search(query: str, k: int = 5) -> List[Dict[str, Any]]:
    coll = get_chroma_collection()
    q = coll.query(
        query_texts=[query],
        n_results=max(k, 1),
        include=["documents", "metadatas", "distances"]
    )
    results = []
    if q and q.get("ids"):
        for i in range(len(q["ids"][0])):
            doc = q["documents"][0][i]
            meta = q["metadatas"][0][i]
            results.append({
                "id": q["ids"][0][i],
                "document": doc,
                "excerpt": _excerpt(doc, query),
                "metadata": meta,
                "distance": float(q["distances"][0][i]),
            })
    return results


def hybrid_search(query: str, k: int = 5) -> List[Dict[str, Any]]:
    # Pull extra candidates from each side, then merge + rerank
    kw = keyword_search(query, k=k * 2)
    vs = vector_search(query, k=k * 2)

    pool: Dict[str, Dict[str, Any]] = {}

    # Normalize BM25 (higher is better)
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

    # Blend scores
    for v in pool.values():
        v["blend"] = 0.5 * v["kw"] + 0.5 * v["vs"]

    merged = sorted(pool.values(), key=lambda x: x["blend"], reverse=True)

    # Dedupe by doc_id (keep best-scoring per document)
    seen_docs = set()
    unique = []
    for m in merged:
        r = m["result"]
        meta = (r.get("metadata") or {})
        doc_id = meta.get("doc_id") or meta.get("docId") or ""
        if doc_id in seen_docs:
            continue
        seen_docs.add(doc_id)
        unique.append(m)
        if len(unique) >= k:
            break

    final: List[Dict[str, Any]] = []
    for m in unique[:k]:
        r = m["result"]
        meta = r.get("metadata", {}) or {}
        doc = r.get("document") or ""
        final.append({
            "id": r["id"],
            "excerpt": _excerpt(doc, query),
            "filename": meta.get("filename"),
            "doc_id": meta.get("doc_id"),
            "chunk_index": meta.get("chunk_index"),
            "source_path": meta.get("source_path"),
            "score_blend": m["blend"],
        })
    return final
