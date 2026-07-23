"""
Wrapper truy xuất dữ liệu: LOCAL FIRST -> Fallback Firestore.

Ưu tiên đọc dữ liệu trực tiếp từ các file local trong thư mục /data:
  - backup.json (books & chapters)
  - processed_chunks.json (chunks + embeddings)
  - processed_summaries.json (tóm tắt chương)

Nếu có file local, hệ thống chạy 100% OFFLINE mà không tốn 1 lượt Read nào của Firestore.
"""
import json
import os
from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore

import config

_app = None
_db = None

# Cache dữ liệu local trong bộ nhớ
_local_books_cache = None
_local_chunks_cache = None
_local_summaries_cache = None


def get_db():
    global _app, _db
    if _db is None:
        cred_json_str = config.FIREBASE_CREDENTIALS_JSON
        cred_path = config.FIREBASE_CREDENTIALS_PATH
        if cred_json_str:
            cred_dict = json.loads(cred_json_str)
            cred = credentials.Certificate(cred_dict)
            _app = firebase_admin.initialize_app(cred)
        elif cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            _app = firebase_admin.initialize_app(cred)
        else:
            # Fallback to Application Default Credentials for Cloud Run / GCP
            _app = firebase_admin.initialize_app()
        _db = firestore.client()
    return _db


# ───────────── LOCAL DATA HELPERS ───────────────────────────────────────────

def _load_local_books() -> dict:
    global _local_books_cache
    if _local_books_cache is not None:
        return _local_books_cache

    candidates = [
        os.path.join(config.DATA_DIR, "backup.json"),
        os.path.join(config.DATA_DIR, "books_export.json"),
        os.path.join("..", config.DATA_DIR, "backup.json"),
        "backup.json",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                _local_books_cache = data.get("books", data)
                return _local_books_cache
            except Exception:
                pass

    _local_books_cache = {}
    return _local_books_cache


def _load_local_chunks() -> dict:
    global _local_chunks_cache
    if _local_chunks_cache is not None:
        return _local_chunks_cache

    candidates = [
        os.path.join(config.DATA_DIR, "processed_chunks.json.gz"),
        os.path.join(config.DATA_DIR, "processed_chunks.json"),
        "processed_chunks.json.gz",
        "processed_chunks.json",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                if p.endswith(".gz"):
                    import gzip
                    with gzip.open(p, "rt", encoding="utf-8") as f:
                        _local_chunks_cache = json.load(f)
                else:
                    with open(p, "r", encoding="utf-8") as f:
                        _local_chunks_cache = json.load(f)
                return _local_chunks_cache
            except Exception:
                pass

    _local_chunks_cache = {}
    return _local_chunks_cache


def _load_local_summaries() -> dict:
    global _local_summaries_cache
    if _local_summaries_cache is not None:
        return _local_summaries_cache

    candidates = [
        os.path.join(config.DATA_DIR, "processed_summaries.json"),
        "processed_summaries.json",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    _local_summaries_cache = json.load(f)
                return _local_summaries_cache
            except Exception:
                pass

    _local_summaries_cache = {}
    return _local_summaries_cache


# ────────────────────────── READ BOOKS ──────────────────────────────────────

def get_book(book_id: str) -> Optional[dict]:
    local = _load_local_books()
    if local and book_id in local:
        return local[book_id]

    try:
        doc = get_db().collection("books").document(book_id).get()
        return doc.to_dict() if doc.exists else None
    except Exception:
        return None


def get_all_books() -> list[tuple[str, dict]]:
    local = _load_local_books()
    if local:
        return [(b_id, b_dict) for b_id, b_dict in local.items()]

    try:
        docs = get_db().collection("books").stream()
        return [(d.id, d.to_dict()) for d in docs]
    except Exception:
        return []


def get_book_chapters(book_id: str) -> list[dict]:
    book = get_book(book_id)
    if not book:
        return []
    return book.get("chapters", [])


def get_chapter(book_id: str, chapter_number: int) -> Optional[dict]:
    chapters = get_book_chapters(book_id)
    if not chapters:
        return None

    def _normalize(idx: int, ch):
        if isinstance(ch, str):
            return {"chapter_number": idx + 1, "content": ch}
        return ch

    for i, ch in enumerate(chapters):
        norm = _normalize(i, ch)
        if norm.get("chapter_number") == chapter_number:
            return norm

    idx = chapter_number - 1
    if 0 <= idx < len(chapters):
        return _normalize(idx, chapters[idx])
    return None


def query_books_by_genre(
    genres: list[str], exclude_book_id: Optional[str], limit: int = 5
) -> list[dict]:
    local = _load_local_books()
    if local:
        results = []
        for b_id, data in local.items():
            if exclude_book_id and b_id == exclude_book_id:
                continue
            b_genres = data.get("genres", [])
            # Tìm xem có genre trùng khớp không
            if not genres or any(g.lower() in [bg.lower() for bg in b_genres] for g in genres):
                b_copy = dict(data)
                b_copy["_id"] = b_id
                results.append(b_copy)

        results.sort(key=lambda x: x.get("rating", 0), reverse=True)
        return results[:limit]

    try:
        q = get_db().collection("books")
        if genres:
            q = q.where("genres", "array_contains_any", genres[:10])

        docs = (
            q.order_by("rating", direction=firestore.Query.DESCENDING)
            .limit(limit + 1)
            .stream()
        )
        results = []
        for d in docs:
            if exclude_book_id and d.id == exclude_book_id:
                continue
            data = d.to_dict()
            data["_id"] = d.id
            results.append(data)
            if len(results) >= limit:
                break
        return results
    except Exception:
        return []


# ─────────── CHAPTER SUMMARIES ───────────────────────────────────────────────

def get_chapter_summary(book_id: str, chapter_number: int) -> Optional[str]:
    local = _load_local_summaries()
    doc_id = f"{book_id}_ch{chapter_number}"
    if local and doc_id in local:
        return local[doc_id].get("summary")

    try:
        doc = get_db().collection("book_chapter_summaries").document(doc_id).get()
        if doc.exists:
            return doc.to_dict().get("summary")
    except Exception:
        pass
    return None


def save_chapter_summary(
    book_id: str,
    chapter_number: int,
    summary: str,
    chapter_title: str = "",
):
    doc_id = f"{book_id}_ch{chapter_number}"
    try:
        get_db().collection("book_chapter_summaries").document(doc_id).set({
            "book_id": book_id,
            "chapter_number": chapter_number,
            "chapter_title": chapter_title,
            "summary": summary,
        })
    except Exception:
        pass


def get_all_chapter_summaries(book_id: str) -> list[dict]:
    local = _load_local_summaries()
    if local:
        results = [v for v in local.values() if v.get("book_id") == book_id]
        results.sort(key=lambda x: x.get("chapter_number", 0))
        return results

    try:
        docs = (
            get_db()
            .collection("book_chapter_summaries")
            .where("book_id", "==", book_id)
            .order_by("chapter_number", direction=firestore.Query.ASCENDING)
            .stream()
        )
        return [d.to_dict() for d in docs]
    except Exception:
        return []


# ────────────── BOOK CHUNKS ───────────────────────────────────────────────────

def get_all_chunks(book_id: str) -> list[dict]:
    local = _load_local_chunks()
    if local:
        chunks = [c for c in local.values() if c.get("book_id") == book_id]
        if chunks:
            return chunks

    try:
        docs = (
            get_db()
            .collection("book_chunks")
            .where("book_id", "==", book_id)
            .stream()
        )
        return [d.to_dict() for d in docs]
    except Exception:
        return []


def save_chunk(chunk: dict):
    try:
        get_db().collection("book_chunks").document(chunk["chunk_id"]).set(chunk)
    except Exception:
        pass


# ────────────── METADATA ──────────────────────────────────────────────────────

# TODO: Hiện toàn bộ sách trong hệ thống đều tiếng Anh nên default "en" là an toàn;
# khi hệ thống có sách đa ngôn ngữ, cần bổ sung field "language" (mã ISO 639-1, vd "en", "vi")
# vào lúc tạo document sách, và cập nhật lại các sách cũ chưa có field này.
def get_book_language(book_id: str) -> str:
    book = get_book(book_id)
    if not book:
        return "en"
    return book.get("language", "en")

def count_chapters(book_id: str) -> int:
    local_summaries = _load_local_summaries()
    if local_summaries:
        count = sum(1 for v in local_summaries.values() if v.get("book_id") == book_id)
        if count > 0:
            return count

    chapters = get_book_chapters(book_id)
    if chapters:
        return len(chapters)

    try:
        docs = get_db().collection("rag_chapters").where("book_id", "==", book_id).stream()
        return sum(1 for _ in docs)
    except Exception:
        return 0
