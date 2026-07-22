"""
Semantic chunking: cắt văn bản theo RANH GIỚI NGỮ NGHĨA thay vì cắt cứng
theo số ký tự. Ý tưởng: tách câu, embed từng câu, gộp các câu liên tiếp có
độ tương đồng cao vào cùng 1 chunk, cắt chunk mới khi độ tương đồng giảm
mạnh (chuyển chủ đề) hoặc khi chunk đã đủ dài.
"""
import re

import numpy as np

import config
from ingestion.embedder import embed_batch


def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?…])\s+", text.strip())
    return [s.strip() for s in sentences if s.strip()]


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 0.0


def semantic_chunk_text(text: str, chapter_number: int, book_id: str) -> list[dict]:
    sentences = _split_sentences(text)
    if not sentences:
        return []

    embeddings = embed_batch(sentences)

    raw_chunks: list[list[str]] = []
    current_sentences = [sentences[0]]
    current_tokens = len(sentences[0].split())

    for i in range(1, len(sentences)):
        sim = _cosine(np.array(embeddings[i - 1]), np.array(embeddings[i]))
        sentence_tokens = len(sentences[i].split())

        should_break = (
            sim < config.SEMANTIC_CHUNK_SIMILARITY_THRESHOLD
            or current_tokens + sentence_tokens > config.SEMANTIC_CHUNK_MAX_TOKENS
        )

        if should_break:
            raw_chunks.append(current_sentences)
            overlap_n = config.SEMANTIC_CHUNK_OVERLAP_SENTENCES
            overlap = current_sentences[-overlap_n:] if overlap_n else []
            current_sentences = overlap + [sentences[i]]
            current_tokens = sum(len(s.split()) for s in current_sentences)
        else:
            current_sentences.append(sentences[i])
            current_tokens += sentence_tokens

    if current_sentences:
        raw_chunks.append(current_sentences)

    return [
        {
            "book_id": book_id,
            "chapter_id": f"{book_id}_ch{chapter_number}",
            "chapter_number": chapter_number,
            "chunk_id": f"{book_id}_ch{chapter_number}_c{idx}",
            "text": " ".join(sents),
        }
        for idx, sents in enumerate(raw_chunks)
    ]
