"""
Script xoá dữ liệu ingest BỊ LỖI — chỉ xoá từ sách thứ 5, chương 5 trở đi.
Giữ nguyên toàn bộ dữ liệu đã ingest thành công trước đó.

KHÔNG đụng collection `books` hay `users`.

Cách chạy (từ thư mục gốc book_rag/):
    python -m ingestion.cleanup_ingest
"""
from firebase.firestore_client import get_db, get_all_books


def cleanup_from_book5_chapter5():
    db = get_db()

    # Lấy danh sách sách cùng thứ tự với ingest script
    books = get_all_books()
    if not books:
        print("⚠️  Không tìm thấy sách nào.")
        return

    print("=" * 60)
    print("CLEANUP — Xoá dữ liệu ingest bị lỗi")
    print("  • Giữ nguyên: sách 1-4 + sách 5 chương 1-4")
    print("  • Xoá: sách 5 từ chương 5 trở đi + sách 6-30")
    print("  • KHÔNG ĐỤNG: books, users")
    print("=" * 60)

    # In danh sách để xác nhận thứ tự
    print("\n📚 Danh sách sách (cùng thứ tự với ingest):\n")
    for i, (book_id, book_data) in enumerate(books, 1):
        title = book_data.get("title", book_id)
        n_ch = len(book_data.get("chapters", []))
        marker = " ← XOÁ TỪ CH.5" if i == 5 else (" ← XOÁ HẾT" if i > 5 else " ✅ GIỮ")
        print(f"  [{i:2d}] {title} ({n_ch} ch.) — ID: {book_id}{marker}")

    print()

    deleted_chunks = 0
    deleted_summaries = 0

    for i, (book_id, book_data) in enumerate(books, 1):
        title = book_data.get("title", book_id)

        if i < 5:
            # Sách 1-4: giữ nguyên
            continue

        if i == 5:
            # Sách thứ 5: lấy hết theo book_id, filter chapter >= 5 trong Python
            print(f"🔧 Sách #{i} '{title}': xoá chunks + summaries từ chương 5...")

            # Xoá chunks: lấy hết rồi filter
            all_chunks = db.collection("book_chunks") \
                .where("book_id", "==", book_id).stream()
            for doc in all_chunks:
                data = doc.to_dict()
                if data.get("chapter_number", 0) >= 5:
                    doc.reference.delete()
                    deleted_chunks += 1

            # Xoá summaries: lấy hết rồi filter
            all_summaries = db.collection("book_chapter_summaries") \
                .where("book_id", "==", book_id).stream()
            for doc in all_summaries:
                data = doc.to_dict()
                if data.get("chapter_number", 0) >= 5:
                    doc.reference.delete()
                    deleted_summaries += 1

            print(f"   🗑️  {deleted_chunks} chunks, {deleted_summaries} summaries đã xoá")

        else:
            # Sách 6-30: xoá toàn bộ (nếu có dữ liệu rác)
            c_count = 0
            chunks = db.collection("book_chunks") \
                .where("book_id", "==", book_id).stream()
            for doc in chunks:
                doc.reference.delete()
                c_count += 1
            deleted_chunks += c_count

            s_count = 0
            summaries = db.collection("book_chapter_summaries") \
                .where("book_id", "==", book_id).stream()
            for doc in summaries:
                doc.reference.delete()
                s_count += 1
            deleted_summaries += s_count

            if c_count or s_count:
                print(f"🗑️  Sách #{i} '{title}': xoá {c_count} chunks, {s_count} summaries")

    print(f"\n✅ Cleanup hoàn tất:")
    print(f"  • Chunks đã xoá:    {deleted_chunks}")
    print(f"  • Summaries đã xoá: {deleted_summaries}")
    print(f"  👉 Chạy lại ingest để resume:")
    print(f"     python -m ingestion.ingest_all_from_firestore")


if __name__ == "__main__":
    cleanup_from_book5_chapter5()
