"""
Bước 1: Tải toàn bộ collection `books` từ Firestore về file local `data/books_export.json`.
Chỉ tốn đúng 30 lượt READ duy nhất!

Cách chạy:
    python -m ingestion.export_books_local
"""
import json
import os
from firebase.firestore_client import get_all_books


def export_books():
    os.makedirs("data", exist_ok=True)
    out_file = os.path.join("data", "books_export.json")

    print("Đang tải danh sách 30 sách từ Firestore về máy...")
    books = get_all_books()

    export_data = {}
    for book_id, book_dict in books:
        export_data[book_id] = book_dict

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

    print(f"Đã lưu {len(export_data)} cuốn sách vào file: '{out_file}' (Chỉ tốn {len(export_data)} reads!)")


if __name__ == "__main__":
    export_books()
