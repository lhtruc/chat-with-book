"""
Semantic search: dùng cho câu hỏi kiểu "sách này nói gì về tiền".
Lấy toàn bộ chunk của sách, so cosine similarity với câu hỏi, lấy top-k.

Lưu ý: cách này load toàn bộ chunk vào RAM mỗi lần query - chấp nhận được
với sách vừa/nhỏ. Nếu sách rất dài hoặc nhiều sách cùng lúc, nên thay bằng
vector DB có index (Firestore vector search extension, Qdrant, Chroma...).
"""
import numpy as np

import config
from firebase.firestore_client import get_all_chunks
from ingestion.embedder import embed_text


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 0.0


def semantic_search(book_id: str, query: str, top_k: int = None) -> dict:
    top_k = top_k or config.RETRIEVAL_TOP_K
    chunks = get_all_chunks(book_id)
    if not chunks:
        return {"chunks": [], "max_similarity_score": 0.0, "found": False}

    query_vec = np.array(embed_text(query))

    scored = []
    for c in chunks:
        emb = c.get("embedding")
        if not emb:
            continue
        score = _cosine_sim(query_vec, np.array(emb))
        scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]
    max_score = top[0][0] if top else 0.0

    return {
        "chunks": [{**c, "score": round(s, 4)} for s, c in top],
        "max_similarity_score": round(max_score, 4),
        "found": max_score >= config.LOW_CONFIDENCE_THRESHOLD,
    }
