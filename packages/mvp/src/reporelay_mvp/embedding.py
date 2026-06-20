"""
Embedding for the MVP. Uses BAAI/bge-small-en-v1.5 (384 dims,
trained on the Pile + C4 + arXiv + StackExchange — strong
technical vocabulary for README-vs-README similarity).

Vectors are L2-normalized (required by BGE's contrastive loss and
recommended for all cosine-similarity use cases).
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

_model: Any = None
_cached_dim: int | None = None

MODEL_NAME = "BAAI/bge-small-en-v1.5"


def _get_model() -> Any:
    global _model, _cached_dim
    if _model is None:
        from sentence_transformers import SentenceTransformer

        logger.info("loading embedding model %s ...", MODEL_NAME)
        start = time.monotonic()
        _model = SentenceTransformer(MODEL_NAME)
        _cached_dim = _model.get_embedding_dimension()
        logger.info(
            "model loaded in %.1fs (dim=%d)", time.monotonic() - start, _cached_dim
        )
    return _model


def embed_text(text_value: str) -> list[float]:
    """Compute a 384-dim embedding for a piece of text. Returns zeros for empty input."""
    if not text_value or not text_value.strip():
        return [0.0] * 384
    model = _get_model()
    vector = model.encode(
        text_value,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return vector.tolist()


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two L2-normalized vectors. Returns 0 for zero vectors."""
    if len(a) != len(b) or not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = (sum(x * x for x in a)) ** 0.5
    norm_b = (sum(x * x for x in b)) ** 0.5
    if norm_a < 1e-9 or norm_b < 1e-9:
        return 0.0
    return dot / (norm_a * norm_b)
