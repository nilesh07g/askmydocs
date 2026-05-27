"""AskMyDocs evaluation harness.

Runs a 10-question golden set against your test PDF and reports:
  - Retrieval accuracy: did we retrieve a chunk from the expected page?
  - Keyword hit rate:   does the generated answer contain expected keywords?

Usage:
    python eval.py path/to/test_document.pdf

Edit the GOLDEN_SET below to match your test PDF.
"""

import os
import sys
import json
import time
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

from rag.config import TOP_K_SPECIFIC, TOP_K_GLOBAL
from rag.ingest import extract_pages, chunk_pages
from rag.embed import load_embedder, build_faiss_index
from rag.retrieve import retrieve_multi
from rag.router import route_query
from rag.answer import build_answer_messages, ask_groq

load_dotenv()


# ---- Edit this golden set for YOUR test PDF ----
# Each entry: question + expected page(s) + expected keyword(s) in answer.
GOLDEN_SET = [
    {"q": "What is the main topic of this document?", "expected_pages": [1, 2], "expected_keywords": []},
    {"q": "Who is the author?", "expected_pages": [1], "expected_keywords": []},
    {"q": "What is the conclusion?", "expected_pages": [], "expected_keywords": []},
    # Add 7 more tailored to your specific test PDF.
]


def run_pipeline(client, user_query, embedder, index, chunks):
    """Same agentic flow as app.py, no Streamlit UI."""
    route_info = route_query(client, user_query, history=[])
    intent = route_info["intent"]
    queries = route_info["search_queries"]

    if intent in ("greeting", "off_topic") or not queries:
        retrieved = []
    elif intent == "global_question":
        retrieved = retrieve_multi(queries, embedder, index, chunks, k_per_query=4, k_total=TOP_K_GLOBAL)
    else:
        retrieved = retrieve_multi(queries or [user_query], embedder, index, chunks,
                                   k_per_query=TOP_K_SPECIFIC, k_total=TOP_K_SPECIFIC)

    messages = build_answer_messages(user_query, retrieved, history=[])
    answer = ask_groq(client, messages)
    return {"answer": answer, "retrieved": retrieved, "route_info": route_info}


def evaluate(pdf_path: str):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("ERROR: Set GROQ_API_KEY in your .env file first.")
        sys.exit(1)

    print(f"\n[1/4] Loading PDF: {pdf_path}")
    with open(pdf_path, "rb") as f:
        pages = extract_pages(f)
    print(f"      Extracted {len(pages)} pages")

    print("[2/4] Chunking + embedding...")
    chunks = chunk_pages(pages)
    embedder = load_embedder()
    index, _ = build_faiss_index(chunks, embedder)
    print(f"      Built FAISS index with {len(chunks)} chunks")

    print(f"[3/4] Running {len(GOLDEN_SET)} eval questions...\n")
    client = Groq(api_key=api_key)

    results = []
    retrieval_hits = 0
    keyword_hits = 0
    questions_with_pages = 0
    questions_with_keywords = 0

    for i, item in enumerate(GOLDEN_SET, 1):
        q = item["q"]
        expected_pages = set(item.get("expected_pages") or [])
        expected_kws = [kw.lower() for kw in item.get("expected_keywords") or []]

        print(f"  Q{i}: {q}")

        out = run_pipeline(client, q, embedder, index, chunks)
        retrieved_pages = {r["page"] for r in out["retrieved"]}
        answer = out["answer"]

        page_hit = None
        if expected_pages:
            questions_with_pages += 1
            page_hit = bool(expected_pages & retrieved_pages)
            if page_hit:
                retrieval_hits += 1

        kw_hit = None
        if expected_kws:
            questions_with_keywords += 1
            answer_lower = answer.lower()
            kw_hit = all(kw in answer_lower for kw in expected_kws)
            if kw_hit:
                keyword_hits += 1

        results.append({
            "question": q,
            "intent": out["route_info"]["intent"],
            "search_queries": out["route_info"]["search_queries"],
            "expected_pages": list(expected_pages),
            "retrieved_pages": sorted(retrieved_pages),
            "page_hit": page_hit,
            "expected_keywords": expected_kws,
            "keyword_hit": kw_hit,
            "answer": answer,
        })

        marker = "✅" if page_hit else ("❌" if page_hit is False else "—")
        print(f"      intent: {out['route_info']['intent']}  retrieval: {marker}  pages={sorted(retrieved_pages)}")
        print(f"      answer: {answer[:140].strip()}{'...' if len(answer) > 140 else ''}\n")
        time.sleep(0.5)  # avoid Groq rate limits

    print("[4/4] Summary")
    print("=" * 50)
    if questions_with_pages:
        acc = retrieval_hits / questions_with_pages * 100
        print(f"  Retrieval accuracy : {retrieval_hits}/{questions_with_pages} ({acc:.0f}%)")
    if questions_with_keywords:
        kw_acc = keyword_hits / questions_with_keywords * 100
        print(f"  Answer keyword hit : {keyword_hits}/{questions_with_keywords} ({kw_acc:.0f}%)")
    print("=" * 50)

    out_path = Path("eval_results.json")
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nFull results written to {out_path.resolve()}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python eval.py path/to/test.pdf")
        sys.exit(1)
    evaluate(sys.argv[1])
