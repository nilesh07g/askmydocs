"""Tunable constants for the RAG pipeline.

Change a number here and the whole app picks it up — useful when experimenting
with chunk sizes, retrieval depth, or swapping models.
"""

# ---- Embedding model ----
# Small (80MB), CPU-friendly, 384-dim vectors. Good default for short-form Q&A.
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

# ---- Chunking ----
# We split each page into overlapping windows so retrieval is precise but
# answers aren't cut off at chunk boundaries.
CHUNK_SIZE = 800       # characters per chunk (~1 paragraph)
CHUNK_OVERLAP = 150    # overlap between consecutive chunks

# ---- Retrieval ----
# How many chunks reach the answerer LLM. Tuning trade-off:
# - Too few → answer is missing context
# - Too many → prompt is diluted with weakly-relevant text and answer quality drops
TOP_K_SPECIFIC = 5     # focused factual questions
TOP_K_GLOBAL = 12      # summary / theme / overview (broader doc coverage needed)

# ---- LLM ----
# Two models, right-sized for the task:
#   - Router: small, fast — intent classification + 3-4 search queries is easy.
#   - Answerer: larger, capable — natural prose synthesis needs reasoning.
# Bonus: the 8B has ~10x the daily free-tier limit, so we burn through fewer
# tokens on every chat message.
LLM_MODEL_ROUTER = "llama-3.1-8b-instant"
LLM_MODEL_ANSWERER = "llama-3.3-70b-versatile"

# Kept so any old `from rag.config import LLM_MODEL` import keeps working.
LLM_MODEL = LLM_MODEL_ANSWERER
