"""
Pipeline chính: routing (tool-calling) -> thực thi tool -> build context -> generation.
Hỗ trợ chuyển đổi linh hoạt giữa DeepSeek và Groq.
"""
from llm.groq_client import run_tool_loop, generate_answer
from llm.prompt_templates import GENERATION_SYSTEM_PROMPT, build_generation_user_message
from retrieval.semantic_retriever import semantic_search
from retrieval.chapter_retriever import get_chapter_content
from retrieval.recommendation_retriever import recommend_books
from retrieval.hybrid_retriever import hybrid_search
from retrieval.metadata_retriever import get_book_metadata
from retrieval.overview_retriever import get_book_overview
from context_builder import build_context_from_chunks
from supabase_db import get_book_language


def run_rag_pipeline(
    book_id: str,
    query: str,
    chat_history: list[dict],
    llm_provider: str = "deepseek",
) -> dict:
    def dispatch(tool_name: str, args: dict) -> dict:
        if tool_name == "semantic_search":
            return semantic_search(book_id, args.get("query", query), args.get("top_k"))
        if tool_name == "get_chapter":
            return get_chapter_content(book_id, args.get("chapter_number"))
        if tool_name == "recommend_books":
            return recommend_books(book_id, args.get("genres", []))
        if tool_name == "hybrid_fallback_search":
            return hybrid_search(book_id, args.get("query", query))
        if tool_name == "get_book_metadata":
            return get_book_metadata(book_id)
        if tool_name == "get_book_overview":
            return get_book_overview(book_id)
        return {"error": f"unknown tool: {tool_name}"}

    book_language = get_book_language(book_id)

    tool_results_by_name, tools_used = run_tool_loop(
        query=query,
        chat_history=chat_history,
        dispatch_fn=dispatch,
        book_language=book_language,
        llm_provider=llm_provider,
    )

    context_text, low_confidence, sources = build_context_from_chunks(tool_results_by_name)

    user_message = build_generation_user_message(query, context_text, low_confidence)
    answer = generate_answer(
        system_prompt=GENERATION_SYSTEM_PROMPT,
        user_message=user_message,
        chat_history=chat_history,
        llm_provider=llm_provider,
    )

    return {
        "answer": answer,
        "sources": sources,
        "tools_used": tools_used,
    }
