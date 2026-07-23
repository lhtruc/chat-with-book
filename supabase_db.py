"""
Supabase Database Access Layer for Book RAG.
Replaces firestore_client.py completely by fetching data directly from Supabase tables:
`books`, `book_chunks`, `book_chapter_summaries`.
"""
from typing import Optional, List, Dict, Any
from supabase_client import get_supabase_client


def get_book(book_id: str) -> Optional[Dict[str, Any]]:
    """Lấy thông tin một cuốn sách từ bảng `books`."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        res = client.table("books").select("*").eq("id", str(book_id)).limit(1).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
    except Exception as e:
        print(f"⚠️ Lỗi get_book({book_id}) từ Supabase: {e}")
    return None


def get_all_books() -> List[Dict[str, Any]]:
    """Lấy toàn bộ danh sách sách từ bảng `books`."""
    client = get_supabase_client()
    if not client:
        return []
    try:
        res = client.table("books").select("*").execute()
        return res.data or []
    except Exception as e:
        print(f"⚠️ Lỗi get_all_books() từ Supabase: {e}")
        return []


def query_books_by_genre(
    genres: List[str],
    exclude_book_id: Optional[str] = None,
    min_rating: float = 0.0,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Tìm danh sách sách gợi ý theo thể loại từ bảng `books`."""
    client = get_supabase_client()
    if not client:
        return []
    try:
        all_books = get_all_books()
        matched = []
        target_genres = set(g.lower() for g in genres)

        for b in all_books:
            b_id = str(b.get("id", ""))
            if exclude_book_id and b_id == str(exclude_book_id):
                continue
            b_rating = float(b.get("rating", 0.0) or 0.0)
            if b_rating < min_rating:
                continue

            b_genres = b.get("genres") or []
            if isinstance(b_genres, str):
                b_genres = [b_genres]
            b_genre_single = b.get("genre")
            if b_genre_single:
                b_genres.append(b_genre_single)

            b_genres_lower = set(g.lower() for g in b_genres)

            # Đánh giá mức độ khớp thể loại
            overlap = len(target_genres.intersection(b_genres_lower))
            if overlap > 0 or not target_genres:
                matched.append((overlap, b_rating, b))

        # Sắp xếp theo mức độ overlap giảm dần, sau đó theo rating giảm dần
        matched.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return [b for _, _, b in matched[:limit]]
    except Exception as e:
        print(f"⚠️ Lỗi query_books_by_genre từ Supabase: {e}")
        return []


def count_chapters(book_id: str) -> int:
    """Đếm số chương của cuốn sách."""
    book = get_book(book_id)
    if book and isinstance(book.get("chapters"), list) and len(book["chapters"]) > 0:
        return len(book["chapters"])

    client = get_supabase_client()
    if not client:
        return 0
    try:
        res = (
            client.table("book_chapter_summaries")
            .select("chapter_number")
            .eq("book_id", str(book_id))
            .execute()
        )
        data = res.data or []
        if data:
            ch_nums = set(item.get("chapter_number") for item in data if item.get("chapter_number") is not None)
            return len(ch_nums)
    except Exception as e:
        print(f"⚠️ Lỗi count_chapters({book_id}) từ Supabase: {e}")
    return 0


def get_chapter(book_id: str, chapter_number: int) -> Optional[Dict[str, Any]]:
    """Lấy thông tin chương từ sách (từ mảng `chapters` trong `books` hoặc ghép từ `book_chunks`)."""
    book = get_book(book_id)
    if book and isinstance(book.get("chapters"), list):
        for ch in book["chapters"]:
            if ch.get("chapter_number") == chapter_number or ch.get("number") == chapter_number:
                return ch

    # Fallback: ghép text các chunks của chương này trong `book_chunks`
    client = get_supabase_client()
    if client:
        try:
            res = (
                client.table("book_chunks")
                .select("content, chunk_index")
                .eq("book_id", str(book_id))
                .eq("chapter_number", chapter_number)
                .order("chunk_index")
                .execute()
            )
            data = res.data or []
            if data:
                full_text = "\n".join(c.get("content", "") for c in data if c.get("content"))
                return {
                    "chapter_number": chapter_number,
                    "chapter_title": f"Chương {chapter_number}",
                    "content": full_text,
                }
        except Exception as e:
            print(f"⚠️ Lỗi get_chapter từ book_chunks: {e}")

    return None


def get_chapter_summary(book_id: str, chapter_number: int) -> Optional[str]:
    """Lấy summary của một chương cụ thể từ bảng `book_chapter_summaries`."""
    client = get_supabase_client()
    if not client:
        return None
    try:
        res = (
            client.table("book_chapter_summaries")
            .select("summary")
            .eq("book_id", str(book_id))
            .eq("chapter_number", chapter_number)
            .limit(1)
            .execute()
        )
        if res.data and len(res.data) > 0:
            return res.data[0].get("summary")
    except Exception as e:
        print(f"⚠️ Lỗi get_chapter_summary từ Supabase: {e}")
    return None


def get_all_chapter_summaries(book_id: str) -> List[Dict[str, Any]]:
    """Lấy danh sách tóm tắt tất cả các chương của sách từ bảng `book_chapter_summaries`."""
    client = get_supabase_client()
    if not client:
        return []
    try:
        res = (
            client.table("book_chapter_summaries")
            .select("chapter_number, chapter_title, summary")
            .eq("book_id", str(book_id))
            .order("chapter_number")
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"⚠️ Lỗi get_all_chapter_summaries({book_id}) từ Supabase: {e}")
        return []


def get_all_chunks(book_id: str) -> List[Dict[str, Any]]:
    """Lấy tất cả chunks của sách từ bảng `book_chunks` (dùng cho fallback hybrid BM25/cosine search)."""
    client = get_supabase_client()
    if not client:
        return []
    try:
        res = (
            client.table("book_chunks")
            .select("id, book_id, chapter_number, chunk_index, content, embedding")
            .eq("book_id", str(book_id))
            .execute()
        )
        data = res.data or []
        chunks = []
        for item in data:
            chunks.append({
                "chunk_id": item.get("id"),
                "book_id": item.get("book_id"),
                "chapter_number": item.get("chapter_number"),
                "chunk_index": item.get("chunk_index"),
                "text": item.get("content"),
                "embedding": item.get("embedding"),
            })
        return chunks
    except Exception as e:
        print(f"⚠️ Lỗi get_all_chunks({book_id}) từ Supabase: {e}")
        return []


def get_book_language(book_id: str) -> str:
    """Xác định ngôn ngữ của cuốn sách (mặc định 'vi')."""
    book = get_book(book_id)
    if book:
        lang = book.get("language")
        if lang:
            return str(lang)
        # Nhận diện đơn giản theo mô tả / tiêu đề nếu cần
        desc = (book.get("description") or "") + " " + (book.get("title") or "")
        if any(c in desc for c in "àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ"):
            return "vi"
    return "vi"
