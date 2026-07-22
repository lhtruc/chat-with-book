"""
Recommendation: dùng cho câu hỏi kiểu "tôi nên đọc sách gì tiếp theo".
Chỉ query metadata (genres, rating) trong collection `books`, không đụng
tới nội dung/embedding của sách.
"""
from firebase.firestore_client import query_books_by_genre


def recommend_books(book_id: str, genres: list[str]) -> dict:
    results = query_books_by_genre(genres, exclude_book_id=book_id, limit=5)
    return {
        "found": len(results) > 0,
        "books": [
            {
                "title": b.get("title"),
                "author": b.get("author"),
                "genres": b.get("genres", []),
                "rating": b.get("rating"),
                "description": b.get("description", ""),
            }
            for b in results
        ],
    }
