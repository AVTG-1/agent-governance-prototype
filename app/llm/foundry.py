"""LLM Foundry: request builders and parsers for its four request families.

Each family has a short list of endpoint variants, tried in order: non-streaming first, then the
streaming endpoint Foundry documents. The variant that worked is remembered per model so later
calls go straight to it, and scripts/probe_llm.py reports it to the presenter.
"""
from __future__ import annotations

import json
import re

from app.llm.catalog import FIXED_TEMPERATURE, NO_SYSTEM_ROLE

AZURE_API_VERSION = "2025-01-01-preview"
MAX_TOKENS = 1500


def auth_header(token: str, project: str) -> str:
    """'Bearer <token>:<project>'; a pasted token that already carries ':suffix' is sent unchanged."""
    token = token.strip()
    return f"Bearer {token}" if ":" in token else f"Bearer {token}:{project}"


# --- Request builders: (path, body) ----------------------------------------------------------

def openai_messages(model_id: str, system: str, user: str) -> list[dict]:
    if model_id in NO_SYSTEM_ROLE:
        return [{"role": "user", "content": f"{system}\n\n{user}"}]
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def openai_body(model_id: str, system: str, user: str, *, stream: bool, response_format: bool,
                temperature: bool, include_model: bool) -> dict:
    body: dict = {}
    if include_model:
        body["model"] = model_id
    body["messages"] = openai_messages(model_id, system, user)
    if temperature and model_id not in FIXED_TEMPERATURE:
        body["temperature"] = 0
    body["stream"] = stream
    if response_format:
        body["response_format"] = {"type": "json_object"}
    return body


def azure_request(deployment: str, system: str, user: str, *, stream=False, response_format=True,
                  temperature=True) -> tuple[str, dict]:
    path = f"/azure/openai/deployments/{deployment}/chat/completions?api-version={AZURE_API_VERSION}"
    return path, openai_body(deployment, system, user, stream=stream, response_format=response_format,
                             temperature=temperature, include_model=False)


def openai_request(model: str, system: str, user: str, *, stream=False, response_format=True,
                   temperature=True) -> tuple[str, dict]:
    return "/openai/v1/chat/completions", openai_body(model, system, user, stream=stream,
                                                      response_format=response_format,
                                                      temperature=temperature, include_model=True)


def bedrock_request(model_id: str, system: str, user: str, *, stream=False) -> tuple[str, dict]:
    path = f"/bedrock/{model_id}/{'converse_stream' if stream else 'converse'}"
    return path, {
        "system": [{"text": system}],
        "messages": [{"role": "user", "content": [{"text": user}]}],
        "inferenceConfig": {"temperature": 0, "maxTokens": MAX_TOKENS},
    }


def gemini_request(model: str, system: str, user: str, *, stream=False, json_mime=True) -> tuple[str, dict]:
    path = (f"/gemini/v1beta/models/{model}:streamGenerateContent?alt=sse" if stream
            else f"/gemini/v1beta/models/{model}:generateContent")
    config: dict = {"temperature": 0}
    if json_mime:
        config["responseMimeType"] = "application/json"
    return path, {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": config,
    }


# --- Variants per family ---------------------------------------------------------------------

def variants(family: str, json_mode: bool) -> list[dict]:
    """Ordered endpoint variants. `name` is what the probe reports."""
    if family in ("azure", "openai"):
        vs = [
            {"name": "non-stream", "stream": False, "response_format": json_mode, "temperature": True},
            {"name": "non-stream, no response_format", "stream": False, "response_format": False, "temperature": True},
            {"name": "non-stream, default temperature", "stream": False, "response_format": False, "temperature": False},
            {"name": "stream", "stream": True, "response_format": False, "temperature": True},
            {"name": "stream, default temperature", "stream": True, "response_format": False, "temperature": False},
        ]
        seen, out = set(), []
        for v in vs:
            key = (v["stream"], v["response_format"], v["temperature"])
            if key not in seen:
                seen.add(key)
                out.append(v)
        return out
    if family == "bedrock":
        return [{"name": "converse (non-stream)", "stream": False}, {"name": "converse_stream", "stream": True}]
    if family == "gemini":
        out = [{"name": "generateContent (non-stream)", "stream": False, "json_mime": json_mode}]
        if json_mode:
            out.append({"name": "generateContent, no responseMimeType", "stream": False, "json_mime": False})
        out.append({"name": "streamGenerateContent (SSE)", "stream": True, "json_mime": False})
        return out
    raise ValueError(f"unknown family {family}")


def build(family: str, model_id: str, system: str, user: str, v: dict) -> tuple[str, dict]:
    if family == "azure":
        return azure_request(model_id, system, user, stream=v["stream"], response_format=v["response_format"],
                             temperature=v["temperature"])
    if family == "openai":
        return openai_request(model_id, system, user, stream=v["stream"], response_format=v["response_format"],
                              temperature=v["temperature"])
    if family == "bedrock":
        return bedrock_request(model_id, system, user, stream=v["stream"])
    return gemini_request(model_id, system, user, stream=v["stream"], json_mime=v["json_mime"])


# --- Parsers -----------------------------------------------------------------------------------

def parse_openai(data: dict) -> str:
    content = data["choices"][0]["message"]["content"]
    if isinstance(content, list):                       # content parts
        return "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return content or ""


def _sse_payloads(text: str):
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            yield json.loads(payload)
        except json.JSONDecodeError:
            continue


def parse_openai_sse(text: str) -> str:
    out = []
    for obj in _sse_payloads(text):
        for choice in obj.get("choices") or []:
            delta = choice.get("delta") or {}
            if isinstance(delta.get("content"), str):
                out.append(delta["content"])
    return "".join(out)


def parse_bedrock(data: dict) -> str:
    return "".join(part.get("text", "") for part in data["output"]["message"]["content"])


def _json_objects(text: str):
    """Every top-level JSON object embedded in text (event-stream binary decoded leniently, or SSE)."""
    dec = json.JSONDecoder()
    i = 0
    while True:
        i = text.find("{", i)
        if i < 0:
            return
        try:
            obj, end = dec.raw_decode(text, i)
        except json.JSONDecodeError:
            i += 1
            continue
        if isinstance(obj, dict):
            yield obj
        i = end


def parse_bedrock_stream(raw: bytes | str) -> str:
    """Concatenate delta.text from a converse_stream body, whether AWS event-stream binary or SSE."""
    text = raw.decode("utf-8", errors="ignore") if isinstance(raw, bytes) else raw
    out = []
    for obj in _json_objects(text):
        block = obj.get("contentBlockDelta", obj)
        delta = block.get("delta") if isinstance(block, dict) else None
        if isinstance(delta, dict) and isinstance(delta.get("text"), str):
            out.append(delta["text"])
    return "".join(out)


def _gemini_text(obj: dict) -> str:
    cands = obj.get("candidates") or []
    if not cands:
        return ""
    parts = (cands[0].get("content") or {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts if isinstance(p, dict) and not p.get("thought"))


def parse_gemini(data: dict) -> str:
    if isinstance(data, list):                       # some proxies return the stream as a JSON array
        return "".join(_gemini_text(o) for o in data)
    return _gemini_text(data)


def parse_gemini_sse(text: str) -> str:
    return "".join(_gemini_text(o) for o in _sse_payloads(text))


def parse(family: str, stream: bool, body: bytes, content_type: str = "") -> str:
    """Parse a 200 response. Falls back to the streaming parser if a proxy streamed anyway."""
    text = body.decode("utf-8", errors="ignore")
    looks_streamed = stream or "event-stream" in content_type or text.lstrip().startswith("data:") \
        or "vnd.amazon.eventstream" in content_type
    if family in ("azure", "openai"):
        return parse_openai_sse(text) if looks_streamed else parse_openai(json.loads(text))
    if family == "bedrock":
        if looks_streamed or not text.lstrip().startswith("{"):
            return parse_bedrock_stream(body)
        return parse_bedrock(json.loads(text))
    return parse_gemini_sse(text) if looks_streamed else parse_gemini(json.loads(text))


def usage_of(body: bytes) -> dict | None:
    m = re.search(rb'"(usage|usageMetadata)"\s*:\s*(\{[^{}]*\})', body)
    if not m:
        return None
    try:
        return json.loads(m.group(2))
    except json.JSONDecodeError:
        return None
