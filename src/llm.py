"""Google Gemini LLM client wrapper with prompt templates."""
from __future__ import annotations

import os
from typing import Generator

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None

try:
    from google import genai
    from google.genai import types
except Exception as exc:  # pragma: no cover
    genai = None
    types = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


DEFAULT_MODELS = {
    "Gemini (default)": "gemini-3.8-flash",
    "Gemini 2.5 Flash": "gemini-2.5-flash",
    "Gemini 1.5 Flash": "gemini-1.5-flash",
}

_client = None
_current_key = None


def get_token() -> str:
    token = ""
    if st is not None:
        for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
            try:
                if key in st.secrets:
                    token = st.secrets[key]
                    if token:
                        break
            except Exception:
                pass
    if not token:
        for env in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
            token = os.getenv(env, "")
            if token:
                break
    if not token:
        try:
            from dotenv import load_dotenv

            load_dotenv()
            for env in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
                token = os.getenv(env, "")
                if token:
                    break
        except Exception:
            pass
    return token or ""


def configure(token: str) -> None:
    global _client, _current_key
    token = (token or "").strip()
    if not token or token == _current_key:
        return
    if genai is None:
        raise RuntimeError(f"google-genai not installed: {_IMPORT_ERROR}")
    _client = genai.Client(api_key=token)
    _current_key = token
    os.environ.setdefault("GEMINI_API_KEY", token)


def _ensure_client():
    global _client, _current_key
    if _client is None:
        configure(get_token())
    if _client is None:
        raise RuntimeError("Gemini API key not configured.")
    return _client


def stream_response(model, prompt, temperature=0.1, top_p=0.9, max_length=2000):
    client = _ensure_client()
    config = types.GenerateContentConfig(
        temperature=float(temperature),
        top_p=float(top_p),
        max_output_tokens=int(max_length),
    )

    def _gen() -> Generator[str, None, None]:
        try:
            for chunk in client.models.generate_content_stream(
                    model=model, contents=prompt, config=config):
                if chunk.text:
                    yield chunk.text
        except Exception:
            # Fallback: non-streaming
            resp = client.models.generate_content(model=model, contents=prompt, config=config)
            yield getattr(resp, "text", "") or ""

    return _gen()


def build_qa_prompt(pages_context: str, question: str, history: list[dict[str, str]]) -> str:
    hist = ""
    for m in history:
        role = "User" if m["role"] == "user" else "Assistant"
        hist += f"{role}: {m['content']}\n\n"
    return (
        "You are a helpful document assistant. Answer using only the provided context. "
        "Cite page numbers in square brackets like [p.3] when possible. "
        "If the answer is not in the context, say you don't know.\n\n"
        f"CONTEXT:\n{pages_context}\n\n"
        f"CONVERSATION SO FAR:\n{hist}"
        f"Now answer this question concisely:\n{question}"
    )


SUMMARY_PROMPTS = {
    "bullet": {
        "short": "Summarize the document in 5-7 concise bullet points. Use '- ' per bullet.",
        "medium": "Summarize the document in 8-12 detailed bullet points grouped by theme.",
        "long": "Provide a comprehensive bullet-point summary (15+ bullets) with sub-bullets where useful.",
    },
    "paragraph": {
        "short": "Write a short 3-4 sentence summary paragraph of the document.",
        "medium": "Write a medium-length summary (1-2 paragraphs, ~150 words) of the document.",
        "long": "Write a thorough multi-paragraph summary (~300-400 words) covering all major sections.",
    },
    "executive": {
        "short": "Write an executive summary (3 sentences): purpose, key findings, recommendation.",
        "medium": "Write an executive summary (1 paragraph + 3 key takeaways bullets).",
        "long": "Write a detailed executive summary with overview, key findings, risks, and next steps.",
    },
}


def build_summary_prompt(text: str, fmt: str, length: str, language: str) -> str:
    instr = SUMMARY_PROMPTS.get(fmt, SUMMARY_PROMPTS["paragraph"]).get(length, "medium")
    return (
        f"You are an expert summarizer. {instr}\n"
        f"Respond in {language}.\n\n"
        f"DOCUMENT:\n{text[:18000]}\n\n"
        "SUMMARY:"
    )
