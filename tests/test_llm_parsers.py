"""Request shapes and parsers for every Foundry family, non-stream and stream, plus the variant fallbacks."""
import asyncio
import json
import struct
import zlib

import httpx
import pytest

import app.llm as llm
from app.llm import foundry
from app.llm.catalog import FOUNDRY_MODELS, RECOMMENDED, resolve_foundry

FAKE = "fake-test-token-not-real-0000"


# --- captured-style samples ---------------------------------------------------------------------

def aws_event(event_type: str, payload: dict) -> bytes:
    """One AWS event-stream message (prelude, headers, JSON payload, CRCs)."""
    def header(name, value):
        n, v = name.encode(), value.encode()
        return bytes([len(n)]) + n + bytes([7]) + struct.pack(">H", len(v)) + v
    headers = header(":event-type", event_type) + header(":content-type", "application/json") + header(":message-type", "event")
    body = json.dumps(payload).encode()
    total = 12 + len(headers) + len(body) + 4
    prelude = struct.pack(">II", total, len(headers))
    prelude += struct.pack(">I", zlib.crc32(prelude))
    msg = prelude + headers + body
    return msg + struct.pack(">I", zlib.crc32(msg))


BEDROCK_EVENTSTREAM = b"".join([
    aws_event("messageStart", {"p": "abcd", "role": "assistant"}),
    aws_event("contentBlockDelta", {"contentBlockIndex": 0, "delta": {"text": '{"ok"'}, "p": "abcdefgh"}),
    aws_event("contentBlockDelta", {"contentBlockIndex": 0, "delta": {"text": ": true}"}, "p": "ab"}),
    aws_event("contentBlockStop", {"contentBlockIndex": 0, "p": "abc"}),
    aws_event("messageStop", {"p": "a", "stopReason": "end_turn"}),
    aws_event("metadata", {"metrics": {"latencyMs": 412}, "p": "ab", "usage": {"inputTokens": 21, "outputTokens": 7}}),
])
BEDROCK_SSE = (
    'data: {"messageStart":{"role":"assistant"}}\n\n'
    'data: {"contentBlockDelta":{"delta":{"text":"{\\"ok\\""},"contentBlockIndex":0}}\n\n'
    'data: {"contentBlockDelta":{"delta":{"text":": true}"},"contentBlockIndex":0}}\n\n'
    'data: {"messageStop":{"stopReason":"end_turn"}}\n\n'
)
BEDROCK_JSON = {"output": {"message": {"role": "assistant", "content": [{"text": '{"ok": true}'}]}},
                "stopReason": "end_turn", "usage": {"inputTokens": 20, "outputTokens": 6}}
OPENAI_JSON = {"id": "chatcmpl-x", "choices": [{"index": 0, "message": {"role": "assistant", "content": '{"ok": true}'},
                                                "finish_reason": "stop"}],
               "usage": {"prompt_tokens": 20, "completion_tokens": 5}}
OPENAI_SSE = (
    'data: {"choices":[],"prompt_filter_results":[]}\n\n'
    'data: {"choices":[{"delta":{"role":"assistant","content":""},"index":0}]}\n\n'
    'data: {"choices":[{"delta":{"content":"{\\"ok\\""},"index":0}]}\n\n'
    'data: {"choices":[{"delta":{"content":": true}"},"index":0,"finish_reason":"stop"}]}\n\n'
    'data: {"choices":[],"usage":{"prompt_tokens":20,"completion_tokens":5}}\n\n'
    'data: [DONE]\n\n'
)
GEMINI_JSON = {"candidates": [{"content": {"role": "model", "parts": [{"text": "thinking...", "thought": True},
                                                                       {"text": '{"ok": true}'}]}}],
               "usageMetadata": {"promptTokenCount": 12}}
GEMINI_SSE = (
    'data: {"candidates":[{"content":{"parts":[{"text":"{\\"ok\\""}],"role":"model"}}]}\r\n\r\n'
    'data: {"candidates":[{"content":{"parts":[{"text":": true}"}],"role":"model"},"finishReason":"STOP"}]}\r\n\r\n'
)


def test_parsers_non_stream():
    assert foundry.parse_openai(OPENAI_JSON) == '{"ok": true}'
    assert foundry.parse_bedrock(BEDROCK_JSON) == '{"ok": true}'
    assert foundry.parse_gemini(GEMINI_JSON) == '{"ok": true}'          # thought parts skipped
    assert foundry.parse_gemini([GEMINI_JSON]) == '{"ok": true}'


def test_parsers_stream():
    assert foundry.parse_openai_sse(OPENAI_SSE) == '{"ok": true}'
    assert foundry.parse_bedrock_stream(BEDROCK_EVENTSTREAM) == '{"ok": true}'
    assert foundry.parse_bedrock_stream(BEDROCK_SSE) == '{"ok": true}'
    assert foundry.parse_gemini_sse(GEMINI_SSE) == '{"ok": true}'


def test_parse_dispatch_detects_unrequested_streaming():
    assert foundry.parse("azure", False, OPENAI_SSE.encode(), "text/event-stream") == '{"ok": true}'
    assert foundry.parse("bedrock", False, BEDROCK_EVENTSTREAM, "application/vnd.amazon.eventstream") == '{"ok": true}'
    assert foundry.parse("gemini", False, GEMINI_SSE.encode(), "") == '{"ok": true}'


def test_request_shapes():
    path, body = foundry.azure_request("gpt-4.1-mini", "S", "U")
    assert path == "/azure/openai/deployments/gpt-4.1-mini/chat/completions?api-version=2025-01-01-preview"
    assert "model" not in body and body["temperature"] == 0 and body["stream"] is False
    assert body["response_format"] == {"type": "json_object"}
    path, body = foundry.openai_request("gpt-5-mini", "S", "U")
    assert path == "/openai/v1/chat/completions" and body["model"] == "gpt-5-mini" and "temperature" not in body
    assert foundry.openai_request("gpt-5.1", "S", "U")[1]["temperature"] == 0
    path, body = foundry.bedrock_request("us.anthropic.claude-sonnet-4-5-20250929-v1:0", "S", "U")
    assert path == "/bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0/converse"
    assert body["system"] == [{"text": "S"}] and body["inferenceConfig"] == {"temperature": 0, "maxTokens": foundry.MAX_TOKENS}
    assert foundry.bedrock_request("m", "S", "U", stream=True)[0] == "/bedrock/m/converse_stream"
    path, body = foundry.gemini_request("gemini-3-flash-preview", "S", "U")
    assert path == "/gemini/v1beta/models/gemini-3-flash-preview:generateContent"
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    assert foundry.gemini_request("g", "S", "U", stream=True)[0] == "/gemini/v1beta/models/g:streamGenerateContent?alt=sse"
    assert foundry.openai_messages("o1-mini", "S", "U") == [{"role": "user", "content": "S\n\nU"}]


def test_auth_header():
    assert foundry.auth_header("abc", "llmproxy-playground") == "Bearer abc:llmproxy-playground"
    assert foundry.auth_header("abc:myproject", "llmproxy-playground") == "Bearer abc:myproject"


def test_catalog():
    assert len(FOUNDRY_MODELS) == 28
    assert resolve_foundry(RECOMMENDED["foundry"]["agent"]) == ("azure", "gpt-4.1-mini")
    assert resolve_foundry("bedrock:claude-sonnet-4.5")[1] == "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    assert resolve_foundry("gemini:some-new-model") == ("gemini", "some-new-model")
    with pytest.raises(ValueError):
        resolve_foundry("nonsense")


def test_extract_json():
    assert llm.extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert llm.extract_json('Here you go: {"a": 1} hope it helps') == {"a": 1}
    with pytest.raises(ValueError):
        llm.extract_json("no json here")


# --- the variant loop, against a fake gateway (httpx.MockTransport, no network) -----------------

@pytest.fixture
def gateway(monkeypatch):
    seen = []

    def install(handler):
        def make(_ca):
            return httpx.AsyncClient(transport=httpx.MockTransport(lambda r: (seen.append(r), handler(r))[1]))
        monkeypatch.setattr(llm, "_make_client", make)
        llm._variant_memo.clear()
        return seen
    return install


def call(model_ref, provider="foundry"):
    return asyncio.run(llm._call_model(provider, model_ref, FAKE, llm.Settings(), "S", "U"))


def test_bedrock_falls_back_to_converse_stream(gateway):
    seen = gateway(lambda r: httpx.Response(404) if r.url.path.endswith("/converse")
                   else httpx.Response(200, content=BEDROCK_EVENTSTREAM,
                                       headers={"content-type": "application/vnd.amazon.eventstream"}))
    r = call("bedrock:claude-sonnet-4.5")
    assert r.text == '{"ok": true}' and r.variant == "converse_stream"
    assert seen[0].headers["authorization"] == f"Bearer {FAKE}:llmproxy-playground"
    seen.clear()
    call("bedrock:claude-sonnet-4.5")                    # remembered: straight to the working variant
    assert len(seen) == 1 and seen[0].url.path.endswith("/converse_stream")


def test_azure_drops_response_format_on_400(gateway):
    def handler(r):
        body = json.loads(r.content)
        if "response_format" in body:
            return httpx.Response(400, json={"error": {"message": "response_format not supported"}})
        return httpx.Response(200, json=OPENAI_JSON)
    gateway(handler)
    r = call("azure:gpt-4.1-mini")
    assert r.text == '{"ok": true}' and r.variant == "non-stream, no response_format"


def test_azure_stream_fallback(gateway):
    def handler(r):
        if json.loads(r.content)["stream"]:
            return httpx.Response(200, text=OPENAI_SSE, headers={"content-type": "text/event-stream"})
        return httpx.Response(400, json={"error": "streaming required"})
    gateway(handler)
    assert call("azure:gpt-4o-mini").variant == "stream"


def test_gemini_sse_fallback(gateway):
    gateway(lambda r: httpx.Response(200, text=GEMINI_SSE) if "streamGenerateContent" in str(r.url)
            else httpx.Response(404))
    r = call("gemini:gemini-3-flash-preview")
    assert r.text == '{"ok": true}' and r.variant.startswith("streamGenerateContent")


def test_auth_error_is_immediate_and_plain(gateway):
    seen = gateway(lambda r: httpx.Response(401, text="bad token " + FAKE))
    with pytest.raises(llm.LLMError) as e:
        call("azure:gpt-4.1-mini")
    assert e.value.kind == "auth" and "Paste a fresh token" in e.value.message
    assert FAKE not in str(e.value) and len(seen) == 1


def test_all_404_is_not_found(gateway):
    gateway(lambda r: httpx.Response(404))
    with pytest.raises(llm.LLMError) as e:
        call("gemini:gemini-2.5-pro")
    assert e.value.kind == "not_found" and "not found" in e.value.message


def test_openrouter_shape(gateway):
    seen = gateway(lambda r: httpx.Response(200, json=OPENAI_JSON))
    r = call("openai/gpt-4.1-mini", provider="openrouter")
    assert r.text == '{"ok": true}'
    assert str(seen[0].url) == "https://openrouter.ai/api/v1/chat/completions"
    assert seen[0].headers["authorization"] == f"Bearer {FAKE}"
    assert json.loads(seen[0].content)["model"] == "openai/gpt-4.1-mini"


def test_timeout_message(gateway):
    def handler(r):
        raise httpx.ReadTimeout("slow", request=r)
    gateway(handler)
    with pytest.raises(llm.LLMError) as e:
        call("azure:gpt-4.1-mini")
    assert e.value.kind == "timeout" and "VPN or proxy" in e.value.message


def test_probe_script_has_no_token_argument():
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    out = subprocess.run([sys.executable, "scripts/probe_llm.py", "--help"], cwd=root, capture_output=True, text=True)
    assert out.returncode == 0 and "--token" not in out.stdout and "--model" in out.stdout
    lst = subprocess.run([sys.executable, "scripts/probe_llm.py", "--list"], cwd=root, capture_output=True, text=True)
    assert "bedrock:claude-sonnet-4.5" in lst.stdout
