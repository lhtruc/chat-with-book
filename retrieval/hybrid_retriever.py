"""
Hybrid fallback: dùng cho mọi câu hỏi không rõ thuộc 3 loại còn lại
(nhân vật, trích dẫn, cảm nhận chung...). Kết hợp BM25 (từ khóa) + cosine
similarity (ngữ nghĩa) để vẫn có kết quả kể cả khi câu hỏi dùng từ ngữ
không trùng khớp với văn bản gốc.
"""
import numpy as np
from rank_bm25 import BM25Okapi

import config
from supabase_db import get_all_chunks
from ingestion.embedder import embed_text


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


def hybrid_search(book_id: str, query: str, top_k: int = None) -> dict:
    top_k = top_k or config.RETRIEVAL_TOP_K
    chunks = get_all_chunks(book_id)
    if not chunks:
        return {"chunks": [], "max_similarity_score": 0.0, "found": False}

    corpus = [_tokenize(c.get("text", "")) for c in chunks]
    bm25 = BM25Okapi(corpus)
    bm25_scores = bm25.get_scores(_tokenize(query))
    bm25_max = max(bm25_scores) if len(bm25_scores) else 0.0
    bm25_norm = [(s / bm25_max if bm25_max > 0 else 0.0) for s in bm25_scores]

    query_vec = np.array(embed_text(query))

    combined = []
    for i, c in enumerate(chunks):
        emb = c.get("embedding")
        vec_score = 0.0
        if emb:
            if isinstance(emb, str):
                import json
                try:
                    emb = json.loads(emb)
                except Exception:
                    emb = [float(x.strip()) for x in emb.strip("[]").split(",") if x.strip()]
            emb_arr = np.array(emb, dtype=float)
            denom = np.linalg.norm(query_vec) * np.linalg.norm(emb_arr)
            vec_score = float(np.dot(query_vec, emb_arr) / denom) if denom else 0.0

        # trọng số 50/50 giữa từ khóa và ngữ nghĩa - có thể tinh chỉnh sau
        final_score = 0.5 * bm25_norm[i] + 0.5 * vec_score
        combined.append((final_score, c))

    combined.sort(key=lambda x: x[0], reverse=True)
    top = combined[:top_k]
    max_score = top[0][0] if top else 0.0

    return {
        "chunks": [{**c, "score": round(s, 4)} for s, c in top],
        "max_similarity_score": round(max_score, 4),
        "found": max_score >= config.LOW_CONFIDENCE_THRESHOLD,
    }
