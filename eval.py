"""AskMyDocs evaluation harness — RAGAS metrics on a golden set.

Computes four industry-standard RAG metrics for each question:
  - faithfulness        : does the answer match the retrieved context (no hallucination)?
  - answer_relevancy    : does the answer address the question asked?
  - context_precision   : are the retrieved chunks relevant?
  - context_recall      : did we retrieve enough to fully answer (vs ground_truth)?

Usage:
    python eval.py path/to/test_document.pdf

Edit the GOLDEN_SET below to match your test PDF. Each entry needs:
  - q              : the question
  - ground_truth   : the correct answer (used by context_recall + answer_relevancy)
  - expected_pages : optional; for the cheap retrieval-page check we also still run
"""

import os
import sys
import json
import time
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

from rag.config import (
    LLM_MODEL_ANSWERER,
    TOP_K_INITIAL,
    TOP_K_SPECIFIC,
    TOP_K_GLOBAL,
    EMBED_MODEL_NAME,
)
from rag.ingest import extract_pages, chunk_pages
from rag.embed import load_embedder, embed_chunks, build_index_from_vectors
from rag.hybrid import BM25Searcher, retrieve_hybrid
from rag.rerank import load_reranker, rerank
from rag.router import route_query
from rag.answer import build_answer_messages, ask_groq

load_dotenv()


# ---- Edit this golden set for YOUR test PDF ----
# Each entry needs ground_truth for RAGAS (context_recall + answer_relevancy).
GOLDEN_SET = [
    {
        "q": "What is the main topic of this document?",
        "ground_truth": "TODO: write the correct answer here",
        "expected_pages": [1, 2],
    },
    {
        "q": "Who is the author?",
        "ground_truth": "TODO: write the correct answer here",
        "expected_pages": [1],
    },
    # Add 8 more questions tailored to your test PDF.
]


def run_pipeline(client, user_query, embedder, index, chunks, bm25, reranker):
    """Same agentic flow as app.py — no Streamlit UI, returns full result dict."""
    route_info = route_query(client, user_query, history=[])
    intent = route_info["intent"]
    queries = route_info["search_queries"]

    if intent in ("greeting", "off_topic") or not queries:
        retrieved = []
    else:
        final_k = TOP_K_GLOBAL if intent == "global_question" else TOP_K_SPECIFIC
        candidates = retrieve_hybrid(
            queries or [user_query], embedder, index, chunks, bm25,
            k_per_query=6, k_total=TOP_K_INITIAL,
        )
        retrieved = rerank(user_query, candidates, reranker, k=final_k)

    messages = build_answer_messages(user_query, retrieved, history=[])
    answer = ask_groq(client, messages)
    return {"answer": answer, "retrieved": retrieved, "route_info": route_info}


def run_ragas(items: list[dict]):
    """Score the (question, answer, contexts, ground_truth) items with RAGAS."""
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    )
    from langchain_groq import ChatGroq
    from langchain_huggingface import HuggingFaceEmbeddings

    api_key = os.getenv("GROQ_API_KEY")
    judge_llm = ChatGroq(model=LLM_MODEL_ANSWERER, api_key=api_key, temperature=0.0)
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL_NAME)

    dataset = Dataset.from_dict({
        "question": [it["q"] for it in items],
        "answer": [it["answer"] for it in items],
        "contexts": [[c["text"] for c in it["retrieved"]] for it in items],
        "ground_truth": [it.get("ground_truth", "") for it in items],
    })

    return evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=judge_llm,
        embeddings=embeddings,
    )


def evaluate_pdf(pdf_path: str):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("ERROR: Set GROQ_API_KEY in your .env file first.")
        sys.exit(1)

    print(f"\n[1/4] Loading PDF: {pdf_path}")
    with open(pdf_path, "rb") as f:
        pages = extract_pages(f)
    print(f"      Extracted {len(pages)} pages")

    print("[2/4] Chunking + embedding + indexing...")
    chunks = chunk_pages(pages)
    embedder = load_embedder()
    vectors = embed_chunks(chunks, embedder)
    index = build_index_from_vectors(vectors)
    bm25 = BM25Searcher(chunks)
    reranker = load_reranker()
    print(f"      Built index with {len(chunks)} chunks")

    print(f"[3/4] Running pipeline on {len(GOLDEN_SET)} questions...\n")
    client = Groq(api_key=api_key)

    items = []
    page_hits = 0
    questions_with_expected_pages = 0
    for i, q in enumerate(GOLDEN_SET, 1):
        print(f"  Q{i}: {q['q']}")
        out = run_pipeline(client, q["q"], embedder, index, chunks, bm25, reranker)
        retrieved_pages = sorted({r["page"] for r in out["retrieved"]})

        expected = set(q.get("expected_pages") or [])
        if expected:
            questions_with_expected_pages += 1
            if expected & set(retrieved_pages):
                page_hits += 1

        items.append({
            "q": q["q"],
            "ground_truth": q.get("ground_truth", ""),
            "answer": out["answer"],
            "retrieved": out["retrieved"],
            "intent": out["route_info"]["intent"],
            "retrieved_pages": retrieved_pages,
        })
        print(f"      intent={out['route_info']['intent']}  pages={retrieved_pages}")
        print(f"      answer: {out['answer'][:120].strip()}{'...' if len(out['answer']) > 120 else ''}\n")
        time.sleep(0.5)

    print("[4/4] Computing RAGAS metrics (this calls Groq several times, ~30-60s)...")
    try:
        ragas_result = run_ragas(items)
        print("\n=========== RAGAS SCORES ===========")
        for metric, score in ragas_result.items():
            print(f"  {metric:25s} : {score:.3f}")
        print("====================================")
        ragas_dict = {k: float(v) for k, v in ragas_result.items()}
    except Exception as e:
        print(f"\n  ⚠️  RAGAS evaluation failed: {e}")
        print("     (Falling back to keyword/page eval only.)")
        ragas_dict = None

    if questions_with_expected_pages:
        acc = page_hits / questions_with_expected_pages * 100
        print(f"\n  Cheap retrieval check (any expected page hit): "
              f"{page_hits}/{questions_with_expected_pages} ({acc:.0f}%)")

    # Persist results for later comparison
    output = {
        "ragas": ragas_dict,
        "page_hit_rate": page_hits / questions_with_expected_pages
            if questions_with_expected_pages else None,
        "items": [
            {
                "q": it["q"],
                "ground_truth": it["ground_truth"],
                "answer": it["answer"],
                "intent": it["intent"],
                "retrieved_pages": it["retrieved_pages"],
            }
            for it in items
        ],
    }
    out_path = Path("eval_results.json")
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\nFull results written to {out_path.resolve()}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python eval.py path/to/test.pdf")
        sys.exit(1)
    evaluate_pdf(sys.argv[1])
