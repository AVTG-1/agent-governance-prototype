"""OpenRouter: OpenAI chat format with a model slug. Same parsers as Foundry's azure/openai families."""
from __future__ import annotations

from app.llm.foundry import openai_body


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token.strip()}", "HTTP-Referer": "http://localhost",
            "X-Title": "Agent governance demo"}


def request(slug: str, system: str, user: str, v: dict) -> tuple[str, dict]:
    return "/chat/completions", openai_body(slug, system, user, stream=v["stream"],
                                            response_format=v["response_format"],
                                            temperature=v["temperature"], include_model=True)
