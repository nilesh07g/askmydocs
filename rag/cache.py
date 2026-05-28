"""On-disk cache for chunks + embeddings.

Embedding a 200-page PDF takes ~30s on CPU. Caching the result means re-uploading
the same PDF is instant. Key = SHA256 of the file bytes (truncated to 16 chars).
"""

import hashlib
import pickle
from pathlib import Path

import numpy as np

CACHE_DIR = Path(".cache/embeddings")


def pdf_hash(pdf_bytes: bytes) -> str:
    """Stable 16-char content hash for a PDF byte blob."""
    return hashlib.sha256(pdf_bytes).hexdigest()[:16]


def _path_for(file_hash: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{file_hash}.pkl"


def load(file_hash: str) -> dict | None:
    """Return cached {'chunks': [...], 'vectors': ndarray} or None if not cached."""
    p = _path_for(file_hash)
    if not p.exists():
        return None
    try:
        with open(p, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def save(file_hash: str, chunks: list[dict], vectors: np.ndarray) -> None:
    """Persist chunks + vectors so the next upload of the same PDF skips embedding."""
    p = _path_for(file_hash)
    with open(p, "wb") as f:
        pickle.dump({"chunks": chunks, "vectors": vectors}, f)
