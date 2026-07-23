"""
Giao diện Web UI (Streamlit) để test thử hệ thống Book RAG Chat.

Tính năng:
  • Đọc 100% DATA LOCAL từ thư mục /data (backup.json, processed_chunks, processed_summaries).
  • Chọn linh hoạt Model LLM giữa DeepSeek (mặc định) và Groq từ Sidebar.
  • Chat tương tác đa lượt (Chat History).
  • Hiển thị chi tiết Tool đã dùng (semantic_search, get_chapter, recommend_books, hybrid_search).
  • Trích dẫn nguồn tham khảo (Chương, Chunk, đoạn trích dẫn cụ thể).

Cách chạy:
    streamlit run app.py
"""
import json
import os
import streamlit as st

import config
from orchestrator import run_rag_pipeline
from firebase.firestore_client import get_all_books

# --- Streamlit Page Config ---
st.set_page_config(
    page_title="Book RAG Chatbot Playground",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS Styling ---
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .tool-badge {
        display: inline-block;
        background-color: #E0E7FF;
        color: #3730A3;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 0.4rem;
        margin-bottom: 0.4rem;
        border: 1px solid #C7D2FE;
    }
    .provider-badge {
        display: inline-block;
        background-color: #DCFCE7;
        color: #166534;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
        border: 1px solid #86EFAC;
    }
    .source-card {
        background-color: #F8FAFC;
        border-left: 4px solid #3B82F6;
        padding: 0.75rem;
        border-radius: 0 0.5rem 0.5rem 0;
        margin-bottom: 0.5rem;
        font-size: 0.9rem;
    }
    </style>
""",
    unsafe_allow_html=True,
)


@st.cache_data
def load_available_books():
    """Tự động load danh sách sách từ backup.json hoặc Firestore."""
    data_dir = getattr(config, "DATA_DIR", "data")
    backup_paths = [
        os.path.join(data_dir, "backup.json"),
        os.path.join("..", data_dir, "backup.json"),
        "backup.json",
    ]
    for path in backup_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                books = data.get("books", {})
                if books:
                    result = []
                    for b_id, b in books.items():
                        title = b.get("title", b_id)
                        author = b.get("author", "Chưa rõ")
                        result.append({"id": b_id, "title": title, "author": author})
                    return result
            except Exception:
                pass

    # Fallback: Firestore
    try:
        raw = get_all_books()
        if raw:
            return [
                {
                    "id": b_id,
                    "title": b.get("title", b_id),
                    "author": b.get("author", "Chưa rõ"),
                }
                for b_id, b in raw
            ]
    except Exception:
        pass

    return [{"id": "shunned_house", "title": "The Shunned House", "author": "H. P. Lovecraft"}]


# --- SIDEBAR ---
st.sidebar.image(
    "https://img.icons8.com/isometric/100/book.png",
    width=64,
)
st.sidebar.title("📖 Book RAG Test Lab")

books_list = load_available_books()
book_options = {f"{b['title']} (bởi {b['author']})": b for b in books_list}

selected_option = st.sidebar.selectbox(
    "📚 Chọn cuốn sách để chat:",
    options=list(book_options.keys()),
    index=0,
)

selected_book = book_options[selected_option]

st.sidebar.divider()

# --- OPTION CHỌN MODEL LLM ---
provider_option = st.sidebar.radio(
    "🤖 Chọn LLM Model Engine:",
    options=["DeepSeek (mặc định)", "Groq (Llama-3.3-70b)"],
    index=0,
    help="DeepSeek dùng OpenAI-compatible API, Groq dùng Groq API.",
)
llm_provider = "deepseek" if "DeepSeek" in provider_option else "groq"

st.sidebar.divider()
st.sidebar.markdown(f"**Thông tin sách đang chọn:**")
st.sidebar.markdown(f"• **Title:** {selected_book['title']}")
st.sidebar.markdown(f"• **Author:** {selected_book['author']}")
st.sidebar.markdown(f"• **Book ID:** `{selected_book['id']}`")
st.sidebar.markdown("• **Data Source:** `📁 100% Local /data`")

if st.sidebar.button("🧹 Xóa lịch sử chat", use_container_width=True):
    st.session_state.messages = []
    st.rerun()

st.sidebar.divider()
st.sidebar.caption(f"⚡ Engine: **{llm_provider.upper()}** | Embedder: **GPU RTX 2050 (CUDA)**")

# --- MAIN CONTENT ---
st.markdown(
    f"<div class='main-title'>Chat with Book: <i>{selected_book['title']}</i></div>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<div>Đang chạy ở chế độ Local Data với Model: <span class='provider-badge'>⚡ {llm_provider.upper()}</span></div><br/>",
    unsafe_allow_html=True,
)

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "tools_used" in msg and msg["tools_used"]:
            badges = "".join(
                [f"<span class='tool-badge'>🔧 {t}</span>" for t in msg["tools_used"]]
            )
            st.markdown(f"<div>{badges}</div>", unsafe_allow_html=True)
        if "sources" in msg and msg["sources"]:
            with st.expander("📍 Nguồn trích dẫn tham khảo"):
                for s in msg["sources"]:
                    ch_str = f"Chương {s.get('chapter_number')}" if s.get('chapter_number') else "Tổng hợp"
                    chunk_str = f" | Chunk: `{s.get('chunk_id')}`" if s.get('chunk_id') else ""
                    st.markdown(
                        f"""<div class='source-card'>
                        <b>[{ch_str}{chunk_str}]</b><br/>
                        <i>"{s.get('excerpt', '')}"</i>
                        </div>""",
                        unsafe_allow_html=True,
                    )

# --- CHAT INPUT & EXECUTION ---
if prompt := st.chat_input("Nhập câu hỏi của bạn (VD: Chương 1 nói về gì?, Nhân vật chính là ai?)..."):
    # Add User message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Format history for Backend
    history_formatted = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages[:-1]
    ]

    with st.chat_message("assistant"):
        with st.spinner(f"🔍 [{llm_provider.upper()}] Đang suy luận & truy xuất dữ liệu sách local..."):
            try:
                result = run_rag_pipeline(
                    book_id=selected_book["id"],
                    query=prompt,
                    chat_history=history_formatted,
                    llm_provider=llm_provider,
                )

                answer = result.get("answer", "Không nhận được câu trả lời.")
                sources = result.get("sources", [])
                tools_used = result.get("tools_used", [])

                # Render Answer
                st.markdown(answer)

                # Render Tools Used Badges
                if tools_used:
                    badges = "".join(
                        [f"<span class='tool-badge'>🔧 {t}</span>" for t in tools_used]
                    )
                    st.markdown(f"<div style='margin-top:0.5rem;'>{badges}</div>", unsafe_allow_html=True)

                # Render Sources Expander
                if sources:
                    with st.expander("📍 Nguồn trích dẫn tham khảo"):
                        for s in sources:
                            ch_str = f"Chương {s.get('chapter_number')}" if s.get('chapter_number') else "Tổng hợp"
                            chunk_str = f" | Chunk: `{s.get('chunk_id')}`" if s.get('chunk_id') else ""
                            st.markdown(
                                f"""<div class='source-card'>
                                <b>[{ch_str}{chunk_str}]</b><br/>
                                <i>"{s.get('excerpt', '')}"</i>
                                </div>""",
                                unsafe_allow_html=True,
                            )

                # Save Assistant message to state
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "tools_used": tools_used,
                        "sources": sources,
                    }
                )

            except Exception as e:
                st.error(f"❌ Lỗi khi xử lý RAG pipeline: {e}")
