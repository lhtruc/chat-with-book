TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "semantic_search",
            "description": (
                "Tìm các đoạn văn liên quan đến một chủ đề, ý nghĩa, khái niệm "
                "xuyên suốt cuốn sách (ví dụ: sách nói gì về tiền, tình yêu, "
                "cái chết, quyền lực...). Dùng khi câu hỏi mang tính chủ đề, "
                "không giới hạn trong một chương cụ thể."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Chủ đề hoặc khái niệm cần tìm trong sách. Phải viết bằng ngôn ngữ gốc của sách (xem rule trong system prompt), không phải ngôn ngữ của người dùng.",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Số đoạn văn cần lấy, mặc định 6",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_chapter",
            "description": (
                "Lấy nội dung hoặc tóm tắt của một chương cụ thể theo số chương. "
                "Dùng khi người dùng hỏi rõ về một chương (vd: 'chương 3 nói về "
                "điều gì'). Nếu câu hỏi so sánh nhiều chương, hãy gọi tool này "
                "nhiều lần, mỗi lần một số chương khác nhau."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "chapter_number": {
                        "type": "integer",
                        "description": "Số thứ tự chương cần lấy",
                    },
                },
                "required": ["chapter_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_books",
            "description": (
                "Gợi ý sách khác để đọc tiếp theo, dựa trên thể loại và rating. "
                "Dùng khi người dùng hỏi 'nên đọc sách gì tiếp theo', 'sách nào "
                "tương tự cuốn này'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "genres": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Danh sách thể loại liên quan để tìm sách tương tự",
                    },
                },
                "required": ["genres"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hybrid_fallback_search",
            "description": (
                "Tìm kiếm chung, kết hợp từ khóa và ngữ nghĩa, dùng khi câu hỏi "
                "không thuộc rõ 3 loại ở trên - ví dụ hỏi về nhân vật, trích dẫn, "
                "cảm nhận chung, hoặc bất kỳ câu hỏi nào không chắc chắn."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string", 
                        "description": "Nội dung cần tìm. Phải viết bằng ngôn ngữ gốc của sách (xem rule trong system prompt), không phải ngôn ngữ của người dùng."
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_book_metadata",
            "description": (
                "Lấy thông tin cơ bản về cuốn sách. Dùng cho các câu hỏi về tác giả, "
                "thể loại, rating, số chương, hoặc xin mô tả ngắn gọn về sách."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_book_overview",
            "description": (
                "Dùng khi câu hỏi cần thông tin khái quát TOÀN BỘ sách (không phải 1 chương hay 1 chi tiết cụ thể). "
                "Ví dụ: 'câu chuyện chính nói về gì', 'bối cảnh diễn ra khi nào', 'đâu là sự kiện nổi bật nhất'. "
                "Lưu ý: Nếu câu hỏi chỉ cần 1 khía cạnh hoặc từ khóa cụ thể rải rác thì dùng semantic_search thay vì tool này."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]
