import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models.schemas import ChatRequest, ChatResponse
from orchestrator import run_rag_pipeline

app = FastAPI(title="Book RAG Chat API")

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
    try:
        history = [{"role": m.role, "content": m.content} for m in request.chat_history]
        result = run_rag_pipeline(
            book_id=request.book_id,
            query=request.query,
            chat_history=history,
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

