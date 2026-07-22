"""
Tóm tắt từng chương bằng DeepSeek (model deepseek-v4-flash), chạy 1 lần
lúc ingest (offline), lưu sẵn vào Firestore collection `book_chapter_summaries`
để câu hỏi "chương X nói về gì" trả lời tức thì.

DeepSeek dùng OpenAI-compatible API → dùng thư viện `openai`.
Groq vẫn giữ riêng cho tool-calling lúc chat.
"""
from openai import OpenAI

import config

client = OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
)

SUMMARY_PROMPT = (
    "Tóm tắt nội dung chương sách sau trong 3-5 câu, giữ đúng các ý chính, "
    "không thêm thông tin ngoài văn bản gốc, không suy diễn:\n\n{text}"
)


def summarize_chapter(chapter_text: str) -> str:
    response = client.chat.completions.create(
        model=config.DEEPSEEK_MODEL,
        messages=[{"role": "user", "content": SUMMARY_PROMPT.format(text=chapter_text)}],
        temperature=0.2,
    )
    return response.choices[0].message.content
