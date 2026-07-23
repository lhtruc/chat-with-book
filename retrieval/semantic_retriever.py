"""
Semantic search: dùng cho câu hỏi kiểu "sách này nói gì về tiền".
Ưu tiên gọi Supabase pgvector RPC (`match_book_chunks`), fallback về Firestore/Local nếu Supabase chưa được cấu hình.
"""
import numpy as np

import config
from supabase_db import get_all_chunks
from ingestion.embedder import embed_text
from supabase_client import get_supabase_client


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 0.0


def semantic_search(book_id: str, query: str, top_k: int = None) -> dict:
    top_k = top_k or config.RETRIEVAL_TOP_K
    query_vec = embed_text(query)
    if isinstance(query_vec, np.ndarray):
        query_vec = query_vec.tolist()

    # 1. Thử gọi Supabase Vector DB trước
    client = get_supabase_client()
    if client is not None:
        try:
            res = client.rpc(
                "match_book_chunks",
                {
                    "query_embedding": query_vec,
                    "filter_book_id": str(book_id),
                    "match_count": top_k,
                },
            ).execute()

            data = res.data or []
            if data:
                scored_chunks = []
                for item in data:
                    score = float(item.get("similarity", 0.0))
                    scored_chunks.append({
                        "chunk_id": item.get("id"),
                        "book_id": item.get("book_id"),
                        "chapter_number": item.get("chapter_number"),
                        "chunk_index": item.get("chunk_index"),
                        "text": item.get("content"),
                        "score": round(score, 4),
                    })
                max_score = scored_chunks[0]["score"] if scored_chunks else 0.0
                return {
                    "chunks": scored_chunks,
                    "max_similarity_score": round(max_score, 4),
                    "found": max_score >= config.LOW_CONFIDENCE_THRESHOLD,
                }
        except Exception as e:
            print(f"⚠️ Supabase vector search error, falling back to local: {e}")

    # 2. Fallback: Local / Firestore in-memory search
    chunks = get_all_chunks(book_id)
    if not chunks:
        return {"chunks": [], "max_similarity_score": 0.0, "found": False}

    q_arr = np.array(query_vec)
    scored = []
    for c in chunks:
        emb = c.get("embedding")
        if not emb:
            continue
        score = _cosine_sim(q_arr, np.array(emb))
        scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]
    max_score = top[0][0] if top else 0.0

    return {
        "chunks": [{**c, "score": round(s, 4)} for s, c in top],
        "max_similarity_score": round(max_score, 4),
        "found": max_score >= config.LOW_CONFIDENCE_THRESHOLD,
    }
