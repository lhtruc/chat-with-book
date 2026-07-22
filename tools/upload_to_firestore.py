"""
Bước 3: Đẩy file JSON đã xử lý local lên Firestore bằng Batch Write (500 docs/batch).
Tiết kiệm tối đa số lần gọi API Write!

Cách chạy:
    python -m ingestion.upload_to_firestore
"""
import json
import os
from firebase.firestore_client import get_db

CHUNKS_FILE = os.path.join("data", "processed_chunks.json")
SUMMARIES_FILE = os.path.join("data", "processed_summaries.json")


def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def upload_batch():
    db = get_db()
    summaries = load_json(SUMMARIES_FILE)
    chunks = load_json(CHUNKS_FILE)

    if not summaries and not chunks:
        print("⚠️ Không có dữ liệu local nào trong thư mục `data/` để upload.")
        return

    print("=" * 60)
    print("📤 UPLOAD BATCH TỪ LOCAL LÊN FIRESTORE")
    print(f"  • Summaries cần up: {len(summaries)}")
    print(f"  • Chunks cần up:    {len(chunks)}")
    print("=" * 60)

    # 1. Upload Summaries
    print("\n1/2 Đang upload book_chapter_summaries...")
    batch = db.batch()
    count = 0
    total_up = 0
    for doc_id, data in summaries.items():
        ref = db.collection("book_chapter_summaries").document(doc_id)
        batch.set(ref, data)
        count += 1
        total_up += 1
        if count == 400:  # Firestore batch limit là 500
            batch.commit()
            batch = db.batch()
            count = 0
            print(f"  • Đã commit {total_up}/{len(summaries)} summaries...")
    if count > 0:
        batch.commit()
        print(f"  ✅ Đã upload xong {total_up} summaries.")

    # 2. Upload Chunks
    print("\n2/2 Đang upload book_chunks...")
    batch = db.batch()
    count = 0
    total_up = 0
    for doc_id, data in chunks.items():
        ref = db.collection("book_chunks").document(doc_id)
        batch.set(ref, data)
        count += 1
        total_up += 1
        if count == 400:
            batch.commit()
            batch = db.batch()
            count = 0
            print(f"  • Đã commit {total_up}/{len(chunks)} chunks...")
    if count > 0:
        batch.commit()
        print(f"  ✅ Đã upload xong {total_up} chunks.")

    print("\n🎉 HOÀN TẤT UPLOAD TẤT CẢ LÊN FIRESTORE!")


if __name__ == "__main__":
    upload_batch()
