import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models.schemas import ChatRequest, ChatResponse
from orchestrator import run_rag_pipeline

app = FastAPI(
    title="Book RAG Chat API",
    description="API Chat RAG hỏi đáp sách dành cho Android App & Web Client",
    version="1.0.0",
)

# Cấu hình CORS để cho phép ứng dụng Android / Web truy cập
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Endpoint nhận query và book_id từ Android App.
    Server tự động truy xuất (RAG pipeline), gọi tool, tổng hợp ngữ cảnh và trả về câu trả lời.
    """
    try:
        result = run_rag_pipeline(
            book_id=request.book_id,
            query=request.query,
            chat_history=[],
            llm_provider=request.llm_provider or "deepseek",
        )
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)

