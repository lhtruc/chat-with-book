"""
Script ingest 1 cuốn sách từ file JSON local.

Cách chạy (từ thư mục gốc book_rag/):
    python -m ingestion.ingest_book --book-id shunned_house --input book.json

book.json có dạng:
{
  "chapters": [
    {"chapter_number": 1, "chapter_title": "...", "text": "..."},
    {"chapter_number": 2, "chapter_title": "...", "text": "..."}
  ]
}

NGUYÊN TẮC:
  - KHÔNG ghi vào collection `books` hay `users`.
  - Summary → collection MỚI `book_chapter_summaries`.
  - Chunks  → collection MỚI `book_chunks`.
"""
import argparse
import json

from ingestion.chunker import semantic_chunk_text
from ingestion.embedder import embed_text
from ingestion.chapter_summarizer import summarize_chapter
from firebase.firestore_client import save_chunk, save_chapter_summary


def ingest_book(book_id: str, input_path: str):
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for chapter in data["chapters"]:
        number = chapter["chapter_number"]
        title = chapter.get("chapter_title", "")
        text = chapter["text"]

        print(f"[Chương {number}] Đang tóm tắt...")
        summary = summarize_chapter(text)

        save_chapter_summary(
            book_id=book_id,
            chapter_number=number,
            summary=summary,
            chapter_title=title,
        )

        print(f"[Chương {number}] Đang chunk + embed...")
        chunks = semantic_chunk_text(text, number, book_id)
        for c in chunks:
            c["embedding"] = embed_text(c["text"])
            save_chunk(c)

        print(f"[Chương {number}] Xong — {len(chunks)} chunk.")

    print("Hoàn tất ingest sách:", book_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--book-id", required=True)
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    ingest_book(args.book_id, args.input)
