"""
Script batch ingest tất cả các file JSON sách nằm trong 1 thư mục local:

Cách chạy (từ thư mục gốc book_rag/):
    python -m ingestion.ingest_folder --dir ./data_books
"""
import argparse
import glob
import os
from ingestion.ingest_book import ingest_book


def ingest_folder(data_dir: str):
    json_files = glob.glob(os.path.join(data_dir, "*.json"))
    if not json_files:
        print(f"⚠️ Không tìm thấy file .json nào trong thư mục '{data_dir}'")
        return

    print(f"📚 Tìm thấy {len(json_files)} file JSON trong '{data_dir}'")
    for idx, file_path in enumerate(json_files, 1):
        book_id = os.path.splitext(os.path.basename(file_path))[0]
        print(f"\n==========================================")
        print(f"[{idx}/{len(json_files)}] Ingesting sách: {book_id}")
        print(f"==========================================")
        try:
            ingest_book(book_id, file_path)
        except Exception as e:
            print(f"❌ Lỗi khi ingest {book_id}: {e}")

    print("\n🎉 Hoàn tất ingest folder!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, help="Thư mục chứa các file sách .json")
    args = parser.parse_args()
    ingest_folder(args.dir)
