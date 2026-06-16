"""LLM answer generation (the second of two LLM calls per user message).

The router (rag/router.py) still uses Groq's 8B model for cheap intent
classification. The ANSWERER moved to Google Gemini 2.5 Flash because
Llama-3.3-70B exhibited a parametric-drift bug on biographical queries that
prompt engineering alone could not fix (see docs/PROGRESS.md and the LangSmith
trace history for the evidence).

Public functions kept named `ask_groq` / `stream_groq` for backwards-compat
with existing callers in app.py and eval.py — only the internal provider
changed.
"""

import os

from langsmith import traceable
from google import genai
from google.genai import types

from .config import LLM_MODEL_ANSWERER
from .prompts import ANSWERER_SYSTEM


def _format_user_turn(user_query: str, retrieved: list[dict]) -> str:
    """Wrap the user's question with the reference passages for this turn.

    Uses XML tags <context>...</context> and <question>...</question> matching
    the structure declared in ANSWERER_SYSTEM.

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

    Layout — deliberately ZERO history:
      system   = identity + behavior rules
      user     = THIS turn's <context> + <question>

    Why no history? Conversation memory from prior turns AMPLIFIES errors when
    earlier answers were imperfect — the model anchors on its own previous bad
    output and continues that pattern instead of reading the new <context>.
    Follow-ups work via the router (which uses history[-2:] for query
    reformulation), not via the answerer.
    """
    del history  # explicit: history is handled by the router, not the answerer
    return [
        {"role": "system", "content": ANSWERER_SYSTEM},
        {"role": "user", "content": _format_user_turn(user_query, retrieved)},
    ]


# Stop sequences for the answerer call.
#
# Without these, some models hallucinate multi-turn "transcript continuation"
# — after the real answer they emit </context><question>...</question> and
# then answer their own invented question. Truncating at any of these tokens
# forces a clean stop the moment the model tries to start a new fake turn.
_STOP_SEQUENCES = ["</context>", "<context>", "</question>", "<question>"]


def _gemini_client() -> genai.Client:
    """Build a Gemini client from GEMINI_API_KEY in the environment.

    Built fresh per call rather than cached — Streamlit Cloud restarts the
    process anyway, and the cost is negligible. Avoids needing a global.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to your .env (local) or "
            "Streamlit Cloud Secrets (deployed)."
        )
    return genai.Client(api_key=api_key)


def _split_messages(messages: list[dict]) -> tuple[str | None, list[dict]]:
    """Convert OpenAI/Groq-style {role, content} list into Gemini's shape.

    Gemini takes the system prompt as a separate `system_instruction` config
    field (not as a message). Everything else becomes `contents` entries with
    roles "user" or "model".
    """
    system_instruction: str | None = None
    contents: list[dict] = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            system_instruction = content
        else:
            gemini_role = "model" if role == "assistant" else "user"
            contents.append({"role": gemini_role, "parts": [{"text": content}]})
    return system_instruction, contents


def _make_config(temperature: float, system_instruction: str | None):
    return types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
        max_output_tokens=1024,
        stop_sequences=_STOP_SEQUENCES,
    )


@traceable(run_type="llm", name="answerer", metadata={"model": LLM_MODEL_ANSWERER})
def ask_groq(client, messages: list[dict], temperature: float = 0.0) -> str:
    """Non-streaming answerer call — returns the full reply as one string.

    Name kept as `ask_groq` for backwards-compat; provider is Gemini under the
    hood. `client` argument is ignored — we build a Gemini client internally.

    Temperature 0.0 (greedy decoding) maximises faithfulness — the model is
    least likely to drift into parametric knowledge when forced to take the
    highest-probability token at every step.
    """
    del client  # legacy Groq client param — Gemini client built inside
    gemini = _gemini_client()
    system_instruction, contents = _split_messages(messages)
    response = gemini.models.generate_content(
        model=LLM_MODEL_ANSWERER,
        contents=contents,
        config=_make_config(temperature, system_instruction),
    )
    return response.text or ""


@traceable(run_type="llm", name="answerer_stream", metadata={"model": LLM_MODEL_ANSWERER})
def stream_groq(client, messages: list[dict], temperature: float = 0.0):
    """Streaming answerer call — yields text chunks as they arrive.

    Used with st.write_stream in the UI so tokens appear live. Same Gemini
    model + same stop sequences as ask_groq; only the API call type differs.
    """
    del client  # legacy Groq client param — Gemini client built inside
    gemini = _gemini_client()
    system_instruction, contents = _split_messages(messages)
    stream = gemini.models.generate_content_stream(
        model=LLM_MODEL_ANSWERER,
        contents=contents,
        config=_make_config(temperature, system_instruction),
    )
    for chunk in stream:
        if chunk.text:
            yield chunk.text
