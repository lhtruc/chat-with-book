import os
from dotenv import load_dotenv

load_dotenv()

# --- Groq (dùng cho tool-calling lúc chat) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# Kiểm tra danh sách model mới nhất tại https://console.groq.com/docs/models
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# --- DeepSeek (dùng cho summarize chương lúc ingest) ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# --- Firebase ---
FIREBASE_CREDENTIALS_PATH = os.getenv(
    "FIREBASE_CREDENTIALS_PATH", "firebase_credentials.json"
)

# --- Embedding (chạy local, không tốn API call) ---
# Model multilingual để hoạt động tốt cả với sách tiếng Anh lẫn tiếng Việt
EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL_NAME", "paraphrase-multilingual-MiniLM-L12-v2"
)

# --- Semantic chunking ---
SEMANTIC_CHUNK_MAX_TOKENS = int(os.getenv("SEMANTIC_CHUNK_MAX_TOKENS", 350))
SEMANTIC_CHUNK_SIMILARITY_THRESHOLD = float(
    os.getenv("SEMANTIC_CHUNK_SIMILARITY_THRESHOLD", 0.55)
)
SEMANTIC_CHUNK_OVERLAP_SENTENCES = int(
    os.getenv("SEMANTIC_CHUNK_OVERLAP_SENTENCES", 1)
)

# --- Retrieval ---
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", 6))
# Ngưỡng similarity để coi kết quả truy xuất là "đáng tin cậy"
LOW_CONFIDENCE_THRESHOLD = float(os.getenv("LOW_CONFIDENCE_THRESHOLD", 0.35))

# --- Router / tool-calling ---
# Số vòng lặp tool-call tối đa trước khi bắt buộc sinh câu trả lời cuối
MAX_TOOL_CALL_ROUNDS = int(os.getenv("MAX_TOOL_CALL_ROUNDS", 3))
