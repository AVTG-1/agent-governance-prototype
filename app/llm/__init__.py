"""The one LLM module: complete() for the demo's two roles, test_model() for the connection gate.

`_call_model` is the single seam that talks to a provider. Tests replace it with
app/llm/mock.py through a pytest fixture; nothing a presenter can reach selects the mock.
"""
from __future__ import annotations

import asyncio
import json
import re
import ssl
import sys
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
    stop_reason: str | None = None     # "max_tokens" when the provider says the reply was cut off


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
    tested: dict = field(default_factory=dict)         # model ref -> TestResult, every live test this session
    preflight: dict | None = None                      # the last preflight's results (memory only)

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


def _retry_after(value: str | None) -> float:
    """Seconds to wait before the one retry after a 429: the gateway's Retry-After, capped at 8 s."""
    try:
        return min(8.0, max(0.5, float(value)))
    except (TypeError, ValueError):
        return 2.0


async def _try_variants(client, provider, family, base, headers, vs, build, memo_key, model_ref) -> LLMResult:
    errors: list[LLMError] = []
    t0 = time.perf_counter()
    for v in vs:
        path, body = build(v)
        try:
            resp = await client.post(base + path, json=body, headers=headers)
            if resp.status_code == 429:          # rate-limited: back off once, then say so
                await asyncio.sleep(_retry_after(resp.headers.get("retry-after")))
                resp = await client.post(base + path, json=body, headers=headers)
                if resp.status_code == 429:
                    raise LLMError("rate_limit", "429: the gateway is rate-limiting this token. "
                                                 "Wait a few seconds, then retry.", 429)
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
        except UnicodeEncodeError:               # a header can only carry ASCII; never a 500 for this
            raise LLMError("config", secrets_store.TOKEN_NOT_SENDABLE) from None
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
                         foundry.usage_of(resp.content), v["name"], foundry.stop_reason(resp.content))
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

class ContractError(ValueError):
    """A reply that is not the JSON object the contract asks for. `truncated`: the JSON never closed."""

    def __init__(self, message: str, truncated: bool = False) -> None:
        super().__init__(message)
        self.truncated = truncated


_FENCE = re.compile(r"```[a-zA-Z0-9_-]*[ \t]*\n?(.*?)(?:```|$)", re.S)


def _outermost_object(t: str) -> str:
    """The first balanced {...} in t, string-aware. Raises ContractError(truncated=True) if it never closes."""
    start = t.find("{")
    if start < 0:
        raise ContractError("no JSON object in the reply")
    depth, in_str, esc = 0, False, False
    for i in range(start, len(t)):
        ch = t[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return t[start:i + 1]
    raise ContractError("the reply was cut off before the JSON object closed", truncated=True)


def _strip_trailing_commas(t: str) -> str:
    """Remove commas before } or ] that sit outside strings (a common model slip)."""
    out, in_str, esc = [], False, False
    for i, ch in enumerate(t):
        if in_str:
            out.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == ",":
            j = i + 1
            while j < len(t) and t[j] in " \t\r\n":
                j += 1
            if j < len(t) and t[j] in "}]":
                continue
        out.append(ch)
    return "".join(out)


def extract_json(text: str) -> dict:
    """The JSON object in a model reply: strips ``` fences and any prose around it, takes the outermost
    object, and forgives trailing commas. Raises ContractError with a short reason."""
    t = (text or "").strip()
    m = _FENCE.search(t)
    if m and "{" in m.group(1):
        t = m.group(1)
    body = _outermost_object(t)
    for candidate in (body, _strip_trailing_commas(body)):
        try:
            obj = json.loads(candidate)
            break
        except json.JSONDecodeError as e:
            err = e
    else:
        raise ContractError(f"invalid JSON: {err.msg} at character {err.pos}")
    if not isinstance(obj, dict):
        raise ContractError("the reply is not a JSON object")
    return obj


def parse_contract(r: LLMResult, model: type[BaseModel]) -> BaseModel:
    """Validate one reply against its contract. A reply the provider cut off at the output limit is
    reported as cut off, whatever the parser saw."""
    try:
        return model.model_validate(extract_json(r.text))
    except ContractError as e:
        if r.stop_reason == "max_tokens" and not e.truncated:
            raise ContractError(f"{e}; the provider stopped at the output limit", truncated=True) from None
        raise
    except ValidationError as e:
        first = e.errors()[0]
        where = ".".join(str(x) for x in first.get("loc", ())) or "reply"
        raise ContractError(f"{where}: {first.get('msg', 'invalid')}") from None


def retry_suffix(e: ContractError) -> str:
    why = ("Your previous reply was cut off before the JSON ended. Keep every string short."
           if e.truncated else f"Your previous reply could not be used: {e}.")
    return f"\n\n{why} Return only the JSON object, matching the shape above exactly. No prose, no code fences."


def _log_raw(role: str, job: str, r: LLMResult, e: ContractError) -> None:
    """For diagnosis on the presenter's terminal. Model output never contains the token; redact anyway."""
    head = f"[llm] {job or role}: unusable reply from {r.model_ref} ({e}; stop reason {r.stop_reason or 'n/a'}, " \
           f"{len(r.text or '')} chars):"
    print(secrets_store.redact(head), file=sys.stderr, flush=True)
    print(secrets_store.redact((r.text or "")[:6000]), file=sys.stderr, flush=True)


async def complete_json(role: str, system: str, user: str, model: type[BaseModel],
                        job: str = "") -> tuple[BaseModel, LLMResult]:
    """Call, validate; on an unusable reply retry once with the reason appended, then fail visibly."""
    r = await complete(role, system, user)
    try:
        return parse_contract(r, model), r
    except ContractError as e:
        _log_raw(role, job, r, e)
        first = e
    r2 = await complete(role, system, user + retry_suffix(first))
    try:
        return parse_contract(r2, model), r2
    except ContractError as e:
        _log_raw(role, job, r2, e)
        label = f"the {job.replace('_', ' ')}" if job else "its reply"
        if e.truncated:
            raise LLMError("parse", f"The {role} model's reply for {label} was cut off at the output limit twice "
                                    f"({r2.model_ref}). Retry, or switch to a model with JSON mode.") from None
        raise LLMError("parse", f"The {role} model returned unusable JSON twice for {label} ({str(e)[:140]}).") from None
