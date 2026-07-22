"""
Chapter lookup: dùng cho câu hỏi kiểu "chương 3 nói về điều gì".

Đọc nội dung chương từ mảng `chapters` bên trong document books/{book_id}
(READ ONLY — không sửa collection books).  Nếu đã có summary được sinh sẵn
trong collection `book_chapter_summaries` thì ưu tiên dùng summary.
"""
from firebase.firestore_client import get_chapter, get_chapter_summary


def _extract_text(chapter: dict) -> str:
    """Trích nội dung text từ chapter object, hỗ trợ nhiều field name."""
    return (
        chapter.get("content")
        or chapter.get("text")
        or chapter.get("full_text")
        or ""
    )


def get_chapter_content(book_id: str, chapter_number) -> dict:
    if chapter_number is None:
        return {"found": False, "chapter_number": None, "text": ""}

    chapter_number = int(chapter_number)
    chapter = get_chapter(book_id, chapter_number)
    if not chapter:
        return {"found": False, "chapter_number": chapter_number, "text": ""}

    # Ưu tiên summary đã sinh sẵn (từ collection book_chapter_summaries)
    summary = get_chapter_summary(book_id, chapter_number)
    if summary:
        text = summary
    else:
        # Fallback: lấy nội dung gốc từ mảng chapters trong books document
        text = _extract_text(chapter)

    return {
        "found": True,
        "chapter_number": chapter.get("chapter_number", chapter_number),
        "chapter_title": chapter.get("chapter_title") or chapter.get("title", ""),
        "text": text,
    }
