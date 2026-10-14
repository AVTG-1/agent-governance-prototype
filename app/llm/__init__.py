"""The one LLM module: complete() for the demo's two roles, test_model() for the connection gate.

`_call_model` is the single seam that talks to a provider. Tests replace it with
app/llm/mock.py through a pytest fixture; nothing a presenter can reach selects the mock.
"""
from __future__ import annotations

import json
import re
import ssl
import time
from dataclasses import dataclass, field

import httpx
from pydantic import BaseModel, ValidationError

from app import secrets_store
from app.llm import foundry, openrouter
from app.llm.catalog import RECOMMENDED, resolve_foundry
from app.settings import FOUNDRY_BASE_URL, FOUNDRY_DEFAULT_PROJECT, LLM_TIMEOUT_S, OPENROUTER_BASE_URL, ca_bundle

ROLES = ("agent", "investigator")


@dataclass
class Settings:
    provider: str = "foundry"                      # foundry | openrouter
    project: str = FOUNDRY_DEFAULT_PROJECT
    base_url: str = FOUNDRY_BASE_URL
    ca_bundle: str | None = None


@dataclass
class LLMResult:
    text: str
    latency_ms: float
    model_ref: str
    usage: dict | None = None
    variant: str = ""


class LLMError(Exception):
    """kind: auth | timeout | not_found | network | tls | http | parse | config. message is presenter-facing."""

    def __init__(self, kind: str, message: str, status: int | None = None) -> None:
        super().__init__(secrets_store.redact(message))
        self.kind, self.message, self.status = kind, secrets_store.redact(message), status


@dataclass
class TestResult:
    ok: bool
    model_ref: str
    latency_ms: float = 0.0
    message: str = ""
    variant: str = ""


@dataclass
class Connection:
    """Connection state for this process. The token itself lives only in secrets_store."""
    settings: Settings = field(default_factory=Settings)
    models: dict = field(default_factory=lambda: dict(RECOMMENDED["foundry"]))
    tests: dict = field(default_factory=dict)          # role -> TestResult

    @property
    def ready(self) -> bool:
        return bool(secrets_store.get()) and all(
            self.tests.get(r) is not None and self.tests[r].ok and self.tests[r].model_ref == self.models[r]
            for r in ROLES)


CONNECTION = Connection()
_variant_memo: dict[str, str] = {}


def _make_client(ca: str | None) -> httpx.AsyncClient:
    """Honours HTTPS_PROXY / NO_PROXY (trust_env) and an optional corporate CA bundle."""
    verify: ssl.SSLContext | bool = ssl.create_default_context(cafile=ca) if ca else True
    return httpx.AsyncClient(trust_env=True, timeout=LLM_TIMEOUT_S, verify=verify)


def _http_error(status: int, body: bytes) -> LLMError:
    if status in (401, 403):
        return LLMError("auth", f"{status}: token rejected or expired. Paste a fresh token.", status)
    if status == 404:
        return LLMError("not_found", "404: model or endpoint not found on this gateway.", status)
    detail = body.decode("utf-8", errors="ignore").strip().replace("\n", " ")[:160]
    return LLMError("http", f"{status}: {detail or 'error from the gateway'}", status)


async def _call_model(provider: str, model_ref: str, token: str, settings: Settings, system: str, user: str,
                      json_mode: bool = True) -> LLMResult:
    """One live call, trying endpoint variants in order. Raises LLMError with a plain message."""
    if provider == "foundry":
        try:
            family, model_id = resolve_foundry(model_ref)
        except ValueError as e:
            raise LLMError("config", str(e)) from None
        base = (settings.base_url or FOUNDRY_BASE_URL).rstrip("/")
        headers = {"Authorization": foundry.auth_header(token, settings.project or FOUNDRY_DEFAULT_PROJECT)}
        vs = foundry.variants(family, json_mode)
        build = lambda v: foundry.build(family, model_id, system, user, v)  # noqa: E731
    elif provider == "openrouter":
        family, base = "openai", OPENROUTER_BASE_URL
        headers = openrouter.auth_headers(token)
        vs = foundry.variants("openai", json_mode)
        build = lambda v: openrouter.request(model_ref, system, user, v)  # noqa: E731
    else:
        raise LLMError("config", f"Unknown provider {provider}.")

    memo_key = f"{provider}|{model_ref}|{json_mode}"
    if memo_key in _variant_memo:
        vs.sort(key=lambda v: v["name"] != _variant_memo[memo_key])
    async with _make_client(settings.ca_bundle or ca_bundle()) as client:
        return await _try_variants(client, provider, family, base, headers, vs, build, memo_key, model_ref)


async def _try_variants(client, provider, family, base, headers, vs, build, memo_key, model_ref) -> LLMResult:
    errors: list[LLMError] = []
    t0 = time.perf_counter()
    for v in vs:
        path, body = build(v)
        try:
            resp = await client.post(base + path, json=body, headers=headers)
        except httpx.TimeoutException:
            raise LLMError("timeout", f"No response in {LLM_TIMEOUT_S:.0f} s. Check VPN or proxy.") from None
        except httpx.ConnectError as e:
            if "CERTIFICATE" in str(e).upper() or "SSL" in str(e).upper():
                raise LLMError("tls", "TLS verification failed. Set LLM_CA_BUNDLE to your corporate CA file "
                                      "(never disable verification).") from None
            host = base.split("//")[-1].split("/")[0]
            raise LLMError("network", f"Could not reach {host}. Check VPN or proxy.") from None
        except httpx.HTTPError as e:
            raise LLMError("network", f"Network error: {type(e).__name__}. Check VPN or proxy.") from None
        if resp.status_code in (401, 403):
            raise _http_error(resp.status_code, resp.content)
        if resp.status_code != 200:
            errors.append(_http_error(resp.status_code, resp.content))
            continue
        try:
            text = foundry.parse(family, v["stream"], resp.content, resp.headers.get("content-type", ""))
        except (KeyError, IndexError, TypeError, ValueError):
            text = ""
        if not text.strip():
            errors.append(LLMError("parse", "Gateway replied 200 but no text could be read."))
            continue
        _variant_memo[memo_key] = v["name"]
        return LLMResult(text, round((time.perf_counter() - t0) * 1000), model_ref,
                         foundry.usage_of(resp.content), v["name"])
    non404 = [e for e in errors if e.kind != "not_found"]
    raise (non404[-1] if non404 else errors[-1])


async def complete(role: str, system: str, user: str, *, json_mode: bool = True) -> LLMResult:
    token = secrets_store.get()
    if not token:
        raise LLMError("auth", "No token in memory. Paste a token on the connection screen.")
    c = CONNECTION
    return await _call_model(c.settings.provider, c.models[role], token, c.settings, system, user, json_mode)


async def test_model(provider: str, model_ref: str, token: str, settings: Settings) -> TestResult:
    """The gate's tiny live call: the model must answer with JSON {"ok": true}."""
    try:
        r = await _call_model(provider, model_ref, token, settings,
                              "You are a connectivity check. Reply with JSON only.",
                              'Reply with the JSON {"ok": true}', True)
    except LLMError as e:
        return TestResult(False, model_ref, message=e.message)
    try:
        ok = extract_json(r.text).get("ok") is True
    except ValueError:
        ok = False
    msg = "Connected." if ok else "The model answered, but not with the expected JSON."
    return TestResult(ok, model_ref, r.latency_ms, msg, r.variant)


# --- Strict JSON outputs ---------------------------------------------------------------------

def extract_json(text: str) -> dict:
    """Parse a JSON object from model text, tolerating code fences or a sentence around it."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        obj = json.loads(t)
    except json.JSONDecodeError:
        start, end = t.find("{"), t.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("no JSON object in reply") from None
        try:
            obj = json.loads(t[start:end + 1])
        except json.JSONDecodeError as e:
            raise ValueError(f"invalid JSON: {e.msg}") from None
    if not isinstance(obj, dict):
        raise ValueError("reply is not a JSON object")
    return obj


NUDGE = "\n\nReturn only valid JSON that matches the schema above. No prose, no code fences."


async def complete_json(role: str, system: str, user: str, model: type[BaseModel]) -> tuple[BaseModel, LLMResult]:
    """Call, validate with pydantic; on invalid output retry once with a nudge, then fail visibly."""
    r = await complete(role, system, user)
    try:
        return model.model_validate(extract_json(r.text)), r
    except (ValueError, ValidationError):
        pass
    r2 = await complete(role, system, user + NUDGE)
    try:
        return model.model_validate(extract_json(r2.text)), r2
    except (ValueError, ValidationError) as e:
        first = str(e).splitlines()[0][:160]
        raise LLMError("parse", f"The {role} model returned invalid JSON twice ({first}).") from None
