from firebase.firestore_client import get_all_chapter_summaries

def get_book_overview(book_id: str) -> dict:
    summaries = get_all_chapter_summaries(book_id)
    if not summaries:
        return {"found": False, "chapters": []}
    
    return {
        "found": True,
        "chapters": summaries
    }
