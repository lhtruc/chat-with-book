"""
Script upload dữ liệu từ các file local in /data và /backup.json lên Supabase.

Nguồn dữ liệu:
  - data/processed_chunks.json (.gz) -> Bảng `book_chunks`
  - data/processed_summaries.json   -> Bảng `book_chapter_summaries`
  - backup.json                      -> Bảng `books`

Cách dùng:
  python ingestion/upload_to_supabase.py [chunks|summaries|books|all]
"""
import gzip
import json
import os
import sys
import time

# Thêm thư mục gốc vào PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from supabase_client import get_supabase_admin_client


def load_chunks_from_local():
    candidates = [
        os.path.join(config.DATA_DIR, "processed_chunks.json.gz"),
        os.path.join(config.DATA_DIR, "processed_chunks.json"),
        "processed_chunks.json.gz",
        "processed_chunks.json",
    ]
    for path in candidates:
        if os.path.exists(path):
            print(f"📖 Đang đọc file chunks từ: {path} ...")
            try:
                if path.endswith(".gz"):
                    with gzip.open(path, "rt", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                if isinstance(data, dict):
                    return list(data.values())
                elif isinstance(data, list):
                    return data
            except Exception as e:
                print(f"❌ Lỗi đọc file {path}: {e}")
    return []


def load_summaries_from_local():
    candidates = [
        os.path.join(config.DATA_DIR, "processed_summaries.json"),
        "processed_summaries.json",
    ]
    for path in candidates:
        if os.path.exists(path):
            print(f"📖 Đang đọc file summaries từ: {path} ...")
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return list(data.values())
                elif isinstance(data, list):
                    return data
            except Exception as e:
                print(f"❌ Lỗi đọc file {path}: {e}")
    return []


def load_books_from_local():
    candidates = [
        os.path.join(config.DATA_DIR, "backup.json"),
        "backup.json",
    ]
    for path in candidates:
        if os.path.exists(path):
            print(f"📖 Đang đọc file books từ: {path} ...")
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                books = data.get("books", data)
                if isinstance(books, dict):
                    items = []
                    for b_id, b_val in books.items():
                        b_val["id"] = b_id
                        items.append(b_val)
                    return items
                elif isinstance(books, list):
                    return books
            except Exception as e:
                print(f"❌ Lỗi đọc file {path}: {e}")
    return []


def upload_chunks_to_supabase(batch_size=200):
    client = get_supabase_admin_client()
    if not client:
        print("❌ Chưa cấu hình SUPABASE_URL và SUPABASE_KEY / SUPABASE_SERVICE_KEY trong file .env!")
        return

    chunks = load_chunks_from_local()
    if not chunks:
        print("⚠️ Không tìm thấy dữ liệu chunks trong thư mục data/")
        return

    total = len(chunks)
    print(f"🚀 Tổng số {total} chunks chuẩn bị đẩy lên Supabase (bảng `book_chunks`)...\n")

    records = []
    for c in chunks:
        chunk_id = c.get("chunk_id") or c.get("id")
        book_id = c.get("book_id")
        content = c.get("text") or c.get("content") or ""
        embedding = c.get("embedding")
        ch_num = c.get("chapter_number") or c.get("chapter_index") or 0
        chunk_idx = c.get("chunk_index", 0)

        if not chunk_id or not book_id or not content or not embedding:
            continue

        records.append({
            "id": str(chunk_id),
            "book_id": str(book_id),
            "chapter_number": int(ch_num),
            "chapter_index": int(ch_num),
            "chunk_index": int(chunk_idx),
            "content": str(content),
            "embedding": embedding,
        })

    total_valid = len(records)
    print(f"📦 Đã chuẩn bị {total_valid} bản ghi hợp lệ. Bắt đầu đẩy theo batch {batch_size}...")

    start_time = time.time()
    uploaded = 0

    for i in range(0, total_valid, batch_size):
        batch = records[i : i + batch_size]
        try:
            client.table("book_chunks").upsert(batch, on_conflict="id").execute()
            uploaded += len(batch)
            pct = round((uploaded / total_valid) * 100, 1)
            print(f"   🟢 Đã upload: {uploaded}/{total_valid} chunks ({pct}%)")
        except Exception as e:
            print(f"   ❌ Lỗi khi upload batch [{i}:{i+batch_size}]: {e}")
            if i == 0:
                print(f"   💡 Gợi ý: Hãy kiểm tra schema bảng `book_chunks` trên Supabase!")
                break

    elapsed = round(time.time() - start_time, 2)
    print(f"\n🎉 Hoàn thành upload {uploaded}/{total_valid} chunks lên Supabase trong {elapsed}s!")


def upload_summaries_to_supabase(batch_size=100):
    client = get_supabase_admin_client()
    if not client:
        print("❌ Chưa cấu hình SUPABASE_URL và SUPABASE_KEY / SUPABASE_SERVICE_KEY trong file .env!")
        return

    summaries = load_summaries_from_local()
    if not summaries:
        print("⚠️ Không tìm thấy dữ liệu summaries trong thư mục data/")
        return

    total = len(summaries)
    print(f"🚀 Tổng số {total} summaries chuẩn bị đẩy lên Supabase (bảng `book_chapter_summaries`)...\n")

    records = []
    for s in summaries:
        book_id = s.get("book_id")
        ch_num = s.get("chapter_number") or 0
        summary_text = s.get("summary") or ""
        ch_title = s.get("chapter_title") or ""

        if not book_id or not summary_text:
            continue

        doc_id = f"{book_id}_ch{ch_num}"
        records.append({
            "id": doc_id,
            "book_id": str(book_id),
            "chapter_number": int(ch_num),
            "chapter_title": str(ch_title),
            "summary": str(summary_text),
        })

    total_valid = len(records)
    print(f"📦 Đã chuẩn bị {total_valid} bản ghi summaries hợp lệ. Bắt đầu đẩy...")

    start_time = time.time()
    uploaded = 0

    for i in range(0, total_valid, batch_size):
        batch = records[i : i + batch_size]
        try:
            client.table("book_chapter_summaries").upsert(batch, on_conflict="id").execute()
            uploaded += len(batch)
            print(f"   🟢 Đã upload: {uploaded}/{total_valid} summaries")
        except Exception as e:
            print(f"   ❌ Lỗi khi upload summaries batch [{i}:{i+batch_size}]: {e}")
            break

    elapsed = round(time.time() - start_time, 2)
    print(f"\n🎉 Hoàn thành upload {uploaded}/{total_valid} summaries lên Supabase trong {elapsed}s!")


def _safe_int(val, default=0) -> int:
    if val is None:
        return default
    if isinstance(val, int):
        return val
    import re
    nums = re.findall(r"\d+", str(val))
    return int(nums[0]) if nums else default


def _safe_float(val, default=0.0) -> float:
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    import re
    nums = re.findall(r"[-+]?\d*\.\d+|\d+", str(val))
    return float(nums[0]) if nums else default


def upload_books_to_supabase(batch_size=50):
    client = get_supabase_admin_client()
    if not client:
        print("❌ Chưa cấu hình SUPABASE_URL và SUPABASE_KEY / SUPABASE_SERVICE_KEY trong file .env!")
        return

    books = load_books_from_local()
    if not books:
        print("⚠️ Không tìm thấy dữ liệu books trong backup.json")
        return

    total = len(books)
    print(f"🚀 Tổng số {total} sách chuẩn bị đẩy lên Supabase (bảng `books`)...\n")

    records = []
    for b in books:
        b_id = b.get("id") or b.get("_id")
        if not b_id:
            continue

        records.append({
            "id": str(b_id),
            "title": b.get("title"),
            "author": b.get("author"),
            "description": b.get("description"),
            "cover_url": b.get("coverUrl"),
            "audio_link": b.get("audio_link"),
            "genre": b.get("genre"),
            "genres": b.get("genres", []),
            "rating": _safe_float(b.get("rating"), 0.0),
            "pages": _safe_int(b.get("pages"), 0),
            "duration": str(b.get("duration", "")),
            "chapters": b.get("chapters", []),
        })

    try:
        client.table("books").upsert(records, on_conflict="id").execute()
        print(f"🎉 Hoàn thành upload {len(records)}/{total} sách lên Supabase!")
    except Exception as e:
        print(f"❌ Lỗi khi upload books: {e}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    if target in ("summaries", "all"):
        upload_summaries_to_supabase()
    if target in ("books", "all"):
        upload_books_to_supabase()
    if target in ("chunks",):
        upload_chunks_to_supabase()
