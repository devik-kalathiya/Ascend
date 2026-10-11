"""Thin wrapper around the Groq chat API with retry/backoff and a test override."""
import json
import os
import re
import time
from typing import Callable, Optional

from .config import BASE_DELAY_MS, MAX_RETRIES, get_model

# Tests (and offline demos) can swap the real API for a fake one.
_override: Optional[Callable[..., str]] = None


def set_llm_override(fn: Optional[Callable[..., str]]) -> None:
    """`fn(system=..., user=..., json=...)` returns the raw reply text (or raises)."""
    global _override
    _override = fn


def _get_client():
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set. Add it to Jibun/.env")
    try:
        from groq import Groq
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("The 'groq' package is not installed. Run: pip install groq") from exc
    return Groq(api_key=key, max_retries=0)  # we do our own retrying below


def _is_retryable(err: Exception) -> bool:
    status = getattr(err, "status_code", None) or getattr(err, "status", None)
    if isinstance(status, int) and (status == 429 or status >= 500):
        return True
    if type(err).__name__ in ("APIConnectionError", "APITimeoutError"):
        return True
    return isinstance(err, (ConnectionResetError, TimeoutError))


def _with_retry(make_request):
    attempt = 1
    while True:
        try:
            return make_request()
        except Exception as err:
            if not _is_retryable(err) or attempt > MAX_RETRIES:
                raise
            delay = BASE_DELAY_MS * (2 ** (attempt - 1))
            print(f"  Groq request failed (attempt {attempt}/{MAX_RETRIES}). "
                  f"Retrying in {delay / 1000:g}s...")
            time.sleep(delay / 1000)
            attempt += 1


def chat(system: str, user: str, json_mode: bool = False,
         temperature: float = 0.7, max_tokens: int = 4096) -> str:
    """One chat call. Returns the raw reply text."""
    if _override:
        return _override(system=system, user=user, json=json_mode)

    client = _get_client()
    kwargs = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    res = _with_retry(lambda: client.chat.completions.create(
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        model=get_model(),
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    ))

    content = res.choices[0].message.content if res.choices else None
    if not content:
        raise RuntimeError("Groq returned an empty response.")
    return content


def extract_json(raw: str) -> dict:
    """Pull a JSON object out of a model reply even if it is wrapped in ``` fences or chatter."""
    cleaned = re.sub(r"```(?:json)?", "", raw, flags=re.I).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model reply.")
    return json.loads(cleaned[start:end + 1])
