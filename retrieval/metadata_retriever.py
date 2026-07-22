from firebase.firestore_client import get_book, count_chapters

def get_book_metadata(book_id: str) -> dict:
    book = get_book(book_id)
    if not book:
        return {"found": False}
    
    return {
        "found": True,
        "title": book.get("title", ""),
        "author": book.get("author", ""),
        "genres": book.get("genres", []),
        "rating": book.get("rating", 0),
        "description": book.get("description", ""),
        "chapter_count": count_chapters(book_id)
    }
