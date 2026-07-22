"""
Batch ingest toàn bộ sách đã có sẵn trên Firestore:
  1. Đọc tất cả document trong collection `books` (READ ONLY).
  2. Với mỗi book, duyệt mảng `chapters`.
  3. Mỗi chương: sinh tóm tắt (DeepSeek) → lưu `book_chapter_summaries`,
     semantic chunk + embed → lưu `book_chunks`.

TUYỆT ĐỐI KHÔNG SỬA collection `books` hay `users`.

Tính năng:
  • OPTIMIZED: gom query kiểm tra resume theo từng cuốn sách (tránh tốn quota Firestore).
  • RESUME: tự skip chương đã có summary + chunks.
  • DỪNG SẠCH: khi gặp lỗi API key / Firestore Quota (429) → dừng ngay, in rõ lý do.

Cách chạy (từ thư mục gốc book_rag/):
    python -m ingestion.ingest_all_from_firestore
"""
import sys
import traceback

from firebase.firestore_client import (
    get_db,
    get_all_books,
    save_chunk,
    save_chapter_summary,
)
from ingestion.chunker import semantic_chunk_text
from ingestion.embedder import embed_text
from ingestion.chapter_summarizer import summarize_chapter


# ── Lỗi liên quan API key / Firestore Quota → dừng hẳn ─────────────────────
_FATAL_KEYWORDS = [
    "api key",
    "apikey",
    "authentication",
    "unauthorized",
    "401",
    "403",
    "insufficient_quota",
    "rate_limit",
    "rate limit",
    "429",
    "quota",
    "resourceexhausted",
]


def _is_fatal_error(e: Exception) -> bool:
    """Phát hiện lỗi do hết API key hoặc hết Quota Firestore (429 ResourceExhausted)."""
    msg = str(e).lower()
    return any(kw in msg for kw in _FATAL_KEYWORDS)


def _extract_text(chapter) -> str:
    """Trích nội dung text từ chapter (str hoặc dict)."""
    if isinstance(chapter, str):
        return chapter
    return (
        chapter.get("content")
        or chapter.get("text")
        or chapter.get("full_text")
        or ""
    )


def _get_done_chapters_for_book(book_id: str) -> set[int]:
    """
    Tối ưu Firestore Read Quota:
    Chỉ query Firestore ĐÚNG 2 LẦN cho mỗi cuốn sách để lấy danh sách các chương đã hoàn thành,
    tránh query lặp đi lặp lại hàng trăm lần gây hết Quota miễn phí (50k reads/ngày).
    """
    db = get_db()
    # 1. Lấy danh sách chapter đã có summary
    summary_docs = db.collection("book_chapter_summaries").where("book_id", "==", book_id).stream()
    summaries_done = {
        d.to_dict().get("chapter_number")
        for d in summary_docs
        if d.to_dict().get("chapter_number") is not None
    }

    if not summaries_done:
        return set()

    # 2. Lấy danh sách chapter đã có chunks
    chunk_docs = db.collection("book_chunks").where("book_id", "==", book_id).stream()
    chunks_done = {
        d.to_dict().get("chapter_number")
        for d in chunk_docs
        if d.to_dict().get("chapter_number") is not None
    }

    # Chương được coi là xong nếu ĐÃ CÓ CẢ summary LẪN chunks
    return summaries_done.intersection(chunks_done)


def ingest_all_from_firestore():
    print("=" * 60)
    print("BATCH INGEST — đọc books từ Firestore, chunk + embed")
    print("  • READ ONLY: books, users")
    print("  • WRITE (ADD NEW): book_chunks, book_chapter_summaries")
    print("  • RESUME: tự skip chương đã xong")
    print("=" * 60)

    try:
        books = get_all_books()
    except Exception as e:
        if _is_fatal_error(e):
            print(f"\n🛑 LỖI FIRESTORE QUOTA / CONNECTIVITY KHẢO SÁT SÁCH:")
            print(f"   {e}")
            print("   👉 Đã vượt quá Quota đọc miễn phí của Firestore (50,000 Reads/ngày) hoặc hết Quota.")
            print("   Vui lòng đợi Firestore reset Quota (thường vào 14:00 chiều VN) rồi chạy lại.\n")
            return
        raise e

    if not books:
        print("\n⚠️  Không tìm thấy document nào trong collection 'books'.")
        return

    total_books = len(books)
    total_chunks_all = 0
    total_skipped = 0
    stopped_early = False
    stop_reason = ""

    print(f"\n📚 Tìm thấy {total_books} cuốn sách.\n")

    for idx, (book_id, book_data) in enumerate(books, 1):
        title = book_data.get("title", book_id)
        chapters = book_data.get("chapters", [])

        print(f"{'=' * 60}")
        print(f"[{idx}/{total_books}] 📖 {title}")
        print(f"  ID: {book_id} | Số chương: {len(chapters)}")
        print(f"{'=' * 60}")

        if not chapters:
            print(f"  ⚠️  Sách này không có mảng chapters, bỏ qua.\n")
            continue

        # Lấy set các chương đã làm xong cho cuốn sách này (1 lần duy nhất)
        try:
            done_chapters = _get_done_chapters_for_book(book_id)
        except Exception as e:
            if _is_fatal_error(e):
                print(f"\n🛑 FIRESTORE QUOTA EXCEEDED (429): {e}")
                stopped_early = True
                stop_reason = f"Firestore Quota Exceeded (50k reads/ngày) tại sách '{title}' (#{idx})"
                break
            done_chapters = set()

        book_chunk_count = 0

        for ch_idx, chapter in enumerate(chapters):
            # Parse chapter (str hoặc dict)
            if isinstance(chapter, str):
                number = ch_idx + 1
                ch_title = ""
                text = chapter
            else:
                number = chapter.get("chapter_number", ch_idx + 1)
                ch_title = (
                    chapter.get("chapter_title")
                    or chapter.get("title")
                    or ""
                )
                text = _extract_text(chapter)

            if not text or not text.strip():
                print(f"  ⚠️  [Chương {number}] Không có nội dung text, bỏ qua.")
                continue

            # ── RESUME: skip chương đã hoàn tất ────────────────────────
            if number in done_chapters:
                print(f"  ⏭️  [Chương {number}] Đã có summary + chunks → skip.")
                total_skipped += 1
                continue

            # ── Sinh summary (DeepSeek) ─────────────────────────────────
            print(f"  📝 [Chương {number}] Đang sinh tóm tắt (DeepSeek)...")
            try:
                summary = summarize_chapter(text)
                save_chapter_summary(
                    book_id=book_id,
                    chapter_number=number,
                    summary=summary,
                    chapter_title=ch_title,
                )
            except Exception as e:
                if _is_fatal_error(e):
                    print(f"\n🛑 DỪNG DO LỖI API KEY HOẶC FIRESTORE QUOTA:")
                    print(f"   {e}")
                    stopped_early = True
                    stop_reason = f"Lỗi API/Quota khi tóm tắt sách '{title}', chương {number}"
                    break
                print(f"     ❌ Lỗi khi tóm tắt chương {number}: {e}")

            # ── Chunk + Embed (Local GPU) ───────────────────────────────
            print(f"  ✂️  [Chương {number}] Đang chunk + embed...")
            try:
                chunks = semantic_chunk_text(text, number, book_id)
                for c in chunks:
                    c["embedding"] = embed_text(c["text"])
                    save_chunk(c)
                book_chunk_count += len(chunks)
                print(f"  ✅ [Chương {number}] {len(chunks)} chunks saved.")
            except Exception as e:
                if _is_fatal_error(e):
                    print(f"\n🛑 DỪNG DO LỖI FIRESTORE WRITE QUOTA:")
                    print(f"   {e}")
                    stopped_early = True
                    stop_reason = f"Lỗi Firestore Quota khi lưu chunks cho sách '{title}', chương {number}"
                    break
                print(f"     ❌ Lỗi khi chunk/embed chương {number}: {e}")

        if stopped_early:
            break

        total_chunks_all += book_chunk_count
        print(f"  📊 Tổng {book_chunk_count} chunks mới cho sách '{title}'.\n")

    # ── Báo cáo cuối ────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    if stopped_early:
        print("⚠️  DỪNG SỚM.")
        print(f"   Lý do: {stop_reason}")
        print(f"   Đã skip {total_skipped} chương (đã hoàn tất trước đó).")
        print(f"   Tổng chunks mới lần này: {total_chunks_all}")
        print(f"   👉 Khi Quota reset hoặc cập nhật key, chỉ cần chạy lại lệnh để tiếp tục.")
    else:
        print(f"🎉 HOÀN TẤT! Đã xử lý {total_books} sách.")
        print(f"   Tổng chunks: {total_chunks_all}")
        print(f"   Đã skip (resume): {total_skipped} chương")
    print("=" * 60)


if __name__ == "__main__":
    ingest_all_from_firestore()
