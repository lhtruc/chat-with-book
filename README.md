# Book RAG Chat — backend cho "chat with book"

Backend Python (FastAPI) dùng Groq tool-calling làm router truy xuất, kết
hợp Firestore cho metadata/nội dung sách. Android app (Java) gọi qua REST
API `/chat`.

## 1. Cài đặt

```bash
cd book_rag
pip install uv
uv pip install --system -r requirements.txt

cp .env.example .env
# Điền GROQ_API_KEY và đường dẫn file service account Firebase vào .env
```

Lấy Firebase service account key: Firebase Console → Project settings →
Service accounts → Generate new private key → lưu file JSON, trỏ
`FIREBASE_CREDENTIALS_PATH` tới file đó.

Kiểm tra tên model Groq mới nhất tại https://console.groq.com/docs/models
trước khi chạy — model trong `.env.example` có thể đã đổi tên/deprecated.

## 2. Ingest sách

### 2a. Batch ingest toàn bộ sách từ Firestore (KHUYẾN NGHỊ)

Nếu 30 cuốn sách đã có sẵn trên Firestore (collection `books`, mỗi document
chứa mảng `chapters`), chạy:

```bash
uv run python -m ingestion.ingest_all_from_firestore
```

Script sẽ:
1. Đọc toàn bộ document trong collection `books` (**CHỈ ĐỌC, KHÔNG SỬA**).
2. Duyệt mảng `chapters` của mỗi sách.
3. Sinh tóm tắt chương bằng Groq → lưu vào collection MỚI `book_chapter_summaries`.
4. Semantic chunking + embed → lưu vào collection MỚI `book_chunks`.

### 2b. Ingest 1 cuốn sách từ file JSON local

Chuẩn bị file JSON chứa nội dung theo chương:

```json
{
  "chapters": [
    {"chapter_number": 1, "chapter_title": "...", "text": "..."},
    {"chapter_number": 2, "chapter_title": "...", "text": "..."}
  ]
}
```

Chạy:
```bash
uv run python -m ingestion.ingest_book --book-id shunned_house --input book.json
```

### Nguyên tắc Firestore

- Collection `books` và `users`: **TUYỆT ĐỐI KHÔNG SỬA** (chỉ đọc).
- Dữ liệu RAG ghi vào collection **MỚI**: `book_chunks`, `book_chapter_summaries`.
- `recommend_books` đọc trực tiếp metadata từ `books/{book_id}`.

**Lưu ý Firestore index**: `query_books_by_genre` dùng
`where("genres", "array_contains_any", ...)` kết hợp `order_by("rating")`
— Firestore yêu cầu composite index cho tổ hợp này. Lần chạy đầu tiên nếu
lỗi, Firestore sẽ trả link tạo index tự động trong error log, bấm vào là
xong.

## 3. Chạy server

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Test nhanh:
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"book_id": "shunned_house", "query": "sách này nói gì về tiền?", "chat_history": []}'
```

## 4. API contract cho Android (Java / Retrofit)

**POST** `/chat`

Request:
```json
{
  "book_id": "shunned_house",
  "query": "chương 3 nói về điều gì?",
  "chat_history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

Response:
```json
{
  "answer": "Chương 3 kể về ...",
  "sources": [
    {"chapter_number": 3, "chunk_id": null, "excerpt": "..."}
  ],
  "tools_used": ["get_chapter"]
}
```

Interface Retrofit gợi ý:
```java
public interface BookChatApi {
    @POST("/chat")
    Call<ChatResponse> chat(@Body ChatRequest request);
}
```
Với `ChatRequest`/`ChatResponse` là POJO map đúng field JSON ở trên
(dùng Gson hoặc Moshi converter).

## 5. Cấu trúc dự án

```
book_rag/
├── main.py                        # FastAPI app, endpoint /chat
├── orchestrator.py                # Ráp pipeline: routing -> tool -> context -> generation
├── context_builder.py             # Ghép context có gắn chapter_number, phát hiện low_confidence
├── config.py
├── models/schemas.py              # Pydantic request/response
├── firebase/firestore_client.py   # Wrapper Firestore (READ books, WRITE book_chunks + book_chapter_summaries)
├── llm/
│   ├── groq_client.py             # Vòng lặp tool-calling (multi-tool, multi-round) + generation
│   ├── tool_definitions.py        # 4 tool: semantic_search, get_chapter, recommend_books, hybrid_fallback_search
│   └── prompt_templates.py        # System prompt routing + generation (honesty + citation rule)
├── retrieval/
│   ├── semantic_retriever.py      # Case: "sách nói gì về X"
│   ├── chapter_retriever.py       # Case: "chương N nói về gì"
│   ├── recommendation_retriever.py# Case: "nên đọc sách gì tiếp"
│   └── hybrid_retriever.py        # Fallback: BM25 + vector
└── ingestion/
    ├── chunker.py                 # Semantic chunking
    ├── embedder.py                # sentence-transformers (local, miễn phí)
    ├── chapter_summarizer.py      # Tóm tắt chương bằng Groq
    ├── ingest_book.py             # Script CLI ingest 1 cuốn sách từ JSON local
    └── ingest_all_from_firestore.py # Batch ingest toàn bộ sách từ Firestore
```

## 6. Những điểm đã biết còn cần fix / mở rộng

- `semantic_retriever` và `hybrid_retriever` load toàn bộ chunk của sách
  vào RAM mỗi lần query — ổn với sách vừa/nhỏ, sách rất dài hoặc traffic
  cao nên chuyển sang vector DB có index (Firestore vector search
  extension, Qdrant, Chroma...).
- Chưa có auth/rate limit cho endpoint `/chat` — cần thêm trước khi lên
  production (API key theo user, hoặc verify Firebase ID token từ app).
- Chưa có cache cho câu hỏi lặp lại (có thể cache theo `book_id + query`).
- `MAX_TOOL_CALL_ROUNDS` mặc định 3 — tăng/giảm tuỳ độ phức tạp câu hỏi
  thực tế, theo dõi qua field `tools_used` trong response để tinh chỉnh.
- Câu hỏi về nhân vật hiện rơi vào `hybrid_fallback_search`; nếu cần
  chính xác hơn có thể thêm 1 collection `book_characters` (NER offline)
  + tool `get_character` riêng.

## 7. Firestore collections

## 8. Hướng dẫn Deploy Backend lên Railway

### Bước 1: Chuẩn bị Repository
Push code lên GitHub (file `data/processed_chunks.json` ~465MB đã được `.gitignore` chặn tự động để repo luôn nhẹ).

### Bước 2: Tạo Service trên Railway
1. Vào [Railway.app](https://railway.app/) → **New Project** → **Deploy from GitHub repo** → Chọn repository `book_rag`.
2. Railway sẽ tự động phát hiện `Dockerfile` và build container.

### Bước 3: Tạo Volume & Upload Data
1. Tại tab **Variables / Volumes** của dịch vụ trên Railway, chọn **Add Volume** và mount vào đường dẫn `/app/data`.
2. Dùng Railway CLI hoặc upload dữ liệu từ máy nhà lên Volume `/app/data`:
   - `backup.json`
   - `processed_chunks.json`
   - `processed_summaries.json`

### Bước 4: Cấu hình Environment Variables trên Railway
Thêm các biến môi trường sau trong tab **Variables** trên Railway Dashboard:
- `GROQ_API_KEY`: Key Groq của bạn
- `DEEPSEEK_API_KEY`: Key DeepSeek của bạn
- `FIREBASE_CREDENTIALS_JSON`: Paste toàn bộ nội dung chuỗi JSON trong file `firebase_credentials.json`
- `DATA_DIR`: `data` (hoặc `/app/data`)
- `PORT`: `8080` (hoặc để Railway cấp cổng động)

