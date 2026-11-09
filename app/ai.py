"""Assistant reply generator. Uses the Anthropic API if ANTHROPIC_API_KEY is set,
otherwise a deterministic stub so the project and tests run offline."""
import os
import httpx

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")


def generate_reply(history: list[dict]) -> str:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return f"[stub assistant] You said: {history[-1]['content']}"
    resp = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": MODEL, "max_tokens": 1000, "messages": history},
        timeout=60,
    )
    resp.raise_for_status()
    return "".join(b.get("text", "") for b in resp.json()["content"])
