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
# Groq serves Llama 3.3 70B at sub-second latency for free.
LLM_MODEL = "llama-3.3-70b-versatile"
