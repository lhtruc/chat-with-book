"""
Ghép kết quả từ (các) tool đã gọi thành 1 khối CONTEXT text để đưa vào
prompt sinh câu trả lời, đồng thời trả về:
  - low_confidence: True nếu không có tool nào tìm được dữ liệu đủ tin cậy
    -> dùng để ép model trả lời trung thực "sách không đề cập" thay vì bịa.
  - sources: danh sách structured (chapter_number, chunk_id, excerpt) để
    backend trả về cho app hiển thị "nguồn tham khảo", không phụ thuộc vào
    việc model có trích dẫn đúng trong text hay không.
"""


def build_context_from_chunks(
    tool_results_by_name: dict[str, list[dict]]
) -> tuple[str, bool, list[dict]]:
    blocks: list[str] = []
    sources: list[dict] = []
    any_found = False

    for tool_name, results in tool_results_by_name.items():
        for result in results:
            if tool_name in ("semantic_search", "hybrid_fallback_search"):
                chunks = result.get("chunks", [])
                if result.get("found"):
                    any_found = True
                for c in chunks:
                    blocks.append(
                        f"[Chương {c.get('chapter_number', '?')} — đoạn {c.get('chunk_id', '?')}]\n"
                        f"{c.get('text', '')}"
                    )
                    sources.append(
                        {
                            "chapter_number": c.get("chapter_number"),
                            "chunk_id": c.get("chunk_id"),
                            "excerpt": c.get("text", "")[:200],
                        }
                    )

            elif tool_name == "get_chapter":
                if result.get("found"):
                    any_found = True
                    blocks.append(
                        f"[Chương {result['chapter_number']} — {result.get('chapter_title', '')}]\n"
                        f"{result['text']}"
                    )
                    sources.append(
                        {
                            "chapter_number": result["chapter_number"],
                            "chunk_id": None,
                            "excerpt": result["text"][:200],
                        }
                    )

            elif tool_name == "recommend_books":
                books = result.get("books", [])
                if books:
                    any_found = True
                    lines = [
                        f"- {b['title']} (tác giả: {b.get('author', '?')}, "
                        f"thể loại: {', '.join(b.get('genres', []))}, "
                        f"rating: {b.get('rating', '?')})"
                        for b in books
                    ]
                    blocks.append("[Danh sách sách gợi ý]\n" + "\n".join(lines))

            elif tool_name == "get_book_metadata":
                if result.get("found"):
                    any_found = True
                    blocks.append(
                        f"[Thông tin sách]\n"
                        f"- Tiêu đề: {result.get('title')}\n"
                        f"- Tác giả: {result.get('author')}\n"
                        f"- Thể loại: {', '.join(result.get('genres', []))}\n"
                        f"- Rating: {result.get('rating')}\n"
                        f"- Số chương: {result.get('chapter_count')}\n"
                        f"- Mô tả: {result.get('description')}"
                    )
                    sources.append({
                        "chapter_number": None,
                        "chunk_id": None,
                        "excerpt": "Thông tin tổng quan sách",
                    })

            elif tool_name == "get_book_overview":
                chapters = result.get("chapters", [])
                if result.get("found") and chapters:
                    any_found = True
                    overview_text = ""
                    for ch in chapters:
                        ch_num = ch.get("chapter_number", "?")
                        ch_title = ch.get("chapter_title", "")
                        summary = ch.get("summary", "")
                        title_str = f" — {ch_title}" if ch_title else ""
                        overview_text += f"[Chương {ch_num}{title_str}]: {summary}\n\n"
                    blocks.append(overview_text.strip())
                    sources.append({
                        "chapter_number": None,
                        "chunk_id": None,
                        "excerpt": "Tổng hợp cốt truyện toàn bộ sách",
                    })

    context_text = (
        "\n\n---\n\n".join(blocks) if blocks else "(Không tìm thấy dữ liệu liên quan.)"
    )
    low_confidence = not any_found
    return context_text, low_confidence, sources
