import os
import uvicorn
import gradio as gr
from main import app as fastapi_app

# Giao diện Gradio đơn giản báo trạng thái Server
demo = gr.Interface(
    fn=lambda prompt: "⚡ Book RAG API Server is running live 24/7!",
    inputs=gr.Textbox(lines=2, placeholder="Nhập câu hỏi test server..."),
    outputs="text",
    title="📚 Book RAG Chatbot API Server",
    description="FastAPI Backend cung cấp API RAG hỏi đáp sách cho Android App (/chat, /health).",
)

# Gắn FastAPI app (chứa endpoint /chat và /health) vào Gradio Space
app = gr.mount_gradio_app(fastapi_app, demo, path="/ui")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
