"""
Script xử lý FULL LOCAL từ file `backup.json`:
  1. Đọc dữ liệu 30 sách trực tiếp từ `backup.json` (không đụng Firestore, 0 Firestore Reads).
  2. Tóm tắt chương bằng DeepSeek API.
  3. Chunking + GPU Embedding theo BATCH (CUDA GPU RTX 2050 - siêu nhanh!).
  4. Lưu kết quả đệm liên tục vào:
       - data/processed_chunks.json
       - data/processed_summaries.json

Cách chạy (từ thư mục gốc book_rag/):
    python -m ingestion.process_books_local
"""
import json
import os
import sys
import time

from ingestion.chunker import semantic_chunk_text
from ingestion.embedder import embed_batch
from ingestion.chapter_summarizer import summarize_chapter


import config

def find_backup_file() -> str:
    data_dir = getattr(config, "DATA_DIR", "data")
    candidates = [
        os.path.join(data_dir, "backup.json"),
        os.path.join("..", data_dir, "backup.json"),
        "backup.json",
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return ""


CHUNKS_FILE = os.path.join(getattr(config, "DATA_DIR", "data"), "processed_chunks.json")
SUMMARIES_FILE = os.path.join(getattr(config, "DATA_DIR", "data"), "processed_summaries.json")


def load_json(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_json(data: dict, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _extract_text(chapter) -> str:
    if isinstance(chapter, str):
        return chapter
    if isinstance(chapter, dict):
        return (
            chapter.get("content")
            or chapter.get("text")
            or chapter.get("full_text")
            or ""
        )
    return ""


def process_all_local():
    backup_path = find_backup_file()
    if not backup_path:
        print("Không tìm thấy file `backup.json`!")
        print("Vui lòng kiểm tra file `backup.json`.")
        return

    print(f"Đã tìm thấy backup.json tại: {backup_path}")
    print("Đang đọc dữ liệu sách...")
    with open(backup_path, "r", encoding="utf-8") as f:
        backup_data = json.load(f)

    books_data = backup_data.get("books", {})
    if not books_data:
        print("Không tìm thấy collection 'books' trong file backup.json!")
        return

    processed_chunks = load_json(CHUNKS_FILE)      # map: chunk_id -> chunk dict
    processed_summaries = load_json(SUMMARIES_FILE) # map: doc_id -> summary dict

    total_books = len(books_data)
    print("=" * 65)
    print("XỬ LÝ LOCAL — BATCH GPU CUDA (RTX 2050) + DEEPSEEK")
    print(f"  Tổng số sách trong backup.json: {total_books}")
    print(f"  Đã có sẵn local: {len(processed_summaries)} summaries, {len(processed_chunks)} chunks")
    print("=" * 65)

    start_time_all = time.time()
    total_new_chunks = 0

    for idx, (book_id, book) in enumerate(books_data.items(), 1):
        title = book.get("title", book_id)
        chapters = book.get("chapters", [])

        print(f"\n{'=' * 65}")
        print(f"[{idx}/{total_books}] 📖 {title} (ID: {book_id})")
        print(f"   Số chương: {len(chapters)}")
        print(f"{'=' * 65}")

        if not chapters:
            print("Sách này không có mảng chapters, bỏ qua.")
            continue

        book_new_chunks = 0

        for ch_idx, chapter in enumerate(chapters):
            if isinstance(chapter, str):
                number = ch_idx + 1
                ch_title = ""
                text = chapter
            else:
                number = chapter.get("chapter_number", ch_idx + 1)
                ch_title = chapter.get("chapter_title") or chapter.get("title") or ""
                text = _extract_text(chapter)

            if not text or not text.strip():
                continue

            summary_doc_id = f"{book_id}_ch{number}"

            # 1. Check & Summarize (DeepSeek)
            if summary_doc_id not in processed_summaries:
                print(f"[Chương {number}] Đang tóm tắt (DeepSeek)...")
                try:
                    summary_text = summarize_chapter(text)
                    processed_summaries[summary_doc_id] = {
                        "book_id": book_id,
                        "chapter_number": number,
                        "chapter_title": ch_title,
                        "summary": summary_text,
                    }
                    save_json(processed_summaries, SUMMARIES_FILE)
                except Exception as e:
                    print(f"Lỗi DeepSeek API chương {number}: {e}")
            else:
                print(f"[Chương {number}] Summary đã có sẵn -> skip")

            # 2. Check & Chunk + GPU Batch Embed
            chapter_chunks_exist = any(
                c.get("book_id") == book_id and c.get("chapter_number") == number
                for c in processed_chunks.values()
            )
            if chapter_chunks_exist:
                print(f"[Chương {number}] Chunks đã có sẵn -> skip")
                continue

            print(f"[Chương {number}] Semantic chunking + GPU Batched Embedding...")
            t0 = time.time()
            try:
                chunks = semantic_chunk_text(text, number, book_id)
                if chunks:
                    # BATCH INFERENCE TRÊN GPU CUDA (Siêu nhanh!)
                    texts = [c["text"] for c in chunks]
                    embeddings = embed_batch(texts, batch_size=64)
                    for c, emb in zip(chunks, embeddings):
                        c["embedding"] = emb
                        processed_chunks[c["chunk_id"]] = c

                    save_json(processed_chunks, CHUNKS_FILE)
                    elapsed = time.time() - t0
                    book_new_chunks += len(chunks)
                    print(f"[Chương {number}] Hoàn tất {len(chunks)} chunks trong {elapsed:.2f}s!")
            except Exception as e:
                print(f"Lỗi chunk/embed chương {number}: {e}")

        total_new_chunks += book_new_chunks

    total_time = time.time() - start_time_all
    print("\n" + "=" * 65)
    print("HOÀN TẤT XỬ LÝ FULL LOCAL!")
    print(f"  • Thời gian tổng cộng: {total_time / 60:.2f} phút")
    print(f"  • Tổng số summaries local: {len(processed_summaries)} docs trong '{SUMMARIES_FILE}'")
    print(f"  • Tổng số chunks local:    {len(processed_chunks)} docs trong '{CHUNKS_FILE}'")
    print("=" * 65)


if __name__ == "__main__":
    process_all_local()
