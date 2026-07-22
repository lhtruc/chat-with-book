"""
Sinh embedding local bằng sentence-transformers (GPU/CUDA batched inference)
"""
import torch
from sentence_transformers import SentenceTransformer

import config

_model = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"⚡ [Embedder] Load model '{config.EMBEDDING_MODEL_NAME}' trên thiết bị: {device.upper()}")
        if device == "cuda":
            print(f"[Embedder] Đã kích hoạt GPU: {torch.cuda.get_device_name(0)}")
        else:
            print("[Embedder] Warning: Đang chạy trên CPU (không tìm thấy CUDA)")
        _model = SentenceTransformer(config.EMBEDDING_MODEL_NAME, device=device)
    return _model


def embed_text(text: str) -> list[float]:
    return _get_model().encode(text, normalize_embeddings=True).tolist()


def embed_batch(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    if not texts:
        return []
    embeddings = _get_model().encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return embeddings.tolist()
