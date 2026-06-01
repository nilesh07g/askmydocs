"""LLM answer generation (the second of two LLM calls per user message).

Given the user's query + retrieved chunks + chat history, build the answerer
prompt and call Groq to produce the final natural-language reply.
"""

from groq import Groq
from langsmith import traceable

from .config import LLM_MODEL_ANSWERER
from .prompts import ANSWERER_SYSTEM


def _format_user_turn(user_query: str, retrieved: list[dict]) -> str:
    """Wrap the user's question with the reference passages for this turn.

    Uses XML tags <context>...</context> and <question>...</question> matching
    the structure declared in ANSWERER_SYSTEM. This is the format validated in
    LangSmith Playground that fixed the bio-hallucination + 'Passage N'
    pattern-completion bugs.

    Key design choices:
      - <context> is a closed tag → model treats the excerpts as a finite set,
        not a list to extend
      - [Page N] labels carry the page info without numbering chunks
        (no '1, 2, 3...' sequence for the model to continue)
      - The turn ends with </question> not 'Question:' → no 'Answer:' autocomplete
    """
    if not retrieved:
        return user_query

    excerpts = "\n\n".join(
        f"[Page {r['page']}]\n{r['text']}"
        for r in retrieved
    )
    return f"<context>\n{excerpts}\n</context>\n\n<question>\n{user_query}\n</question>"


def build_answer_messages(
    user_query: str,
    retrieved: list[dict],
    history: list[dict],
) -> list[dict]:
    """Assemble the messages list for the answerer LLM call.

    Layout:
      system   = identity + behavior rules (static; no chunks)
      history  = last few turns of plain Q/A (no chunks repeated)
      user     = THIS turn's chunks + THIS turn's question
    """
    messages = [{"role": "system", "content": ANSWERER_SYSTEM}]
    for turn in history[-6:]:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": _format_user_turn(user_query, retrieved)})
    return messages


@traceable(run_type="llm", name="answerer", metadata={"model": LLM_MODEL_ANSWERER})
def ask_groq(client: Groq, messages: list[dict], temperature: float = 0.0) -> str:
    """Call Groq and return the assistant's reply as a single string (non-streaming).

    Temperature 0.0 (greedy decoding) maximises faithfulness — the LLM is least
    likely to drift into parametric knowledge when forced to take the highest-
    probability token at every step. Trade-off: slightly less varied phrasing.
    """
    completion = client.chat.completions.create(
        model=LLM_MODEL_ANSWERER,
        messages=messages,
        temperature=temperature,
        max_tokens=1024,
    )
    return completion.choices[0].message.content


@traceable(run_type="llm", name="answerer_stream", metadata={"model": LLM_MODEL_ANSWERER})
def stream_groq(client: Groq, messages: list[dict], temperature: float = 0.0):
    """Yield tokens as they arrive from Groq. Used with st.write_stream in the UI.

    Temperature kept at 0.0 to match ask_groq — so RAGAS eval scores reflect
    actual production behavior, not a slightly different (warmer) regime.
    """
    stream = client.chat.completions.create(
        model=LLM_MODEL_ANSWERER,
        messages=messages,
        temperature=temperature,
        max_tokens=1024,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
