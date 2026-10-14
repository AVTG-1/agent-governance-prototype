"""Presenter tool: check a model is reachable from this laptop, and which endpoint variant works.

    python scripts/probe_llm.py --provider foundry --model azure:gpt-4.1-mini
    python scripts/probe_llm.py --provider foundry --model bedrock:claude-sonnet-4.5 --each-variant
    python scripts/probe_llm.py --provider openrouter --model openai/gpt-4.1-mini

The token is asked for interactively (getpass). It is never accepted as an argument or read from a
file, never printed, and never written anywhere.
"""
from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.llm as llm  # noqa: E402
from app import secrets_store  # noqa: E402
from app.llm import foundry  # noqa: E402
from app.llm.catalog import FOUNDRY_MODELS, resolve_foundry  # noqa: E402
from app.settings import FOUNDRY_BASE_URL, FOUNDRY_DEFAULT_PROJECT  # noqa: E402

PROMPT_SYSTEM = "You are a connectivity check. Reply with JSON only."
PROMPT_USER = 'Reply with the JSON {"ok": true}'


async def probe(provider: str, model: str, token: str, settings: llm.Settings) -> int:
    t0 = time.perf_counter()
    try:
        r = await llm._call_model(provider, model, token, settings, PROMPT_SYSTEM, PROMPT_USER, True)
    except llm.LLMError as e:
        print(f"  ✗ {model}: {e.message}  ({(time.perf_counter() - t0) * 1000:.0f} ms)")
        return 1
    try:
        parsed = llm.extract_json(r.text)
    except ValueError:
        parsed = None
    print(f"  ✓ {model}: 200 in {r.latency_ms:.0f} ms")
    print(f"    endpoint variant that worked: {r.variant}")
    print(f"    parsed reply: {parsed if parsed is not None else r.text[:200]!r}")
    return 0 if parsed and parsed.get("ok") is True else 2


async def each_variant(model: str, token: str, settings: llm.Settings) -> None:
    """Try every Foundry endpoint variant on its own, so the presenter knows exactly what works."""
    family, model_id = resolve_foundry(model)
    headers = {"Authorization": foundry.auth_header(token, settings.project)}
    async with llm._make_client(settings.ca_bundle) as client:
        for v in foundry.variants(family, True):
            path, body = foundry.build(family, model_id, PROMPT_SYSTEM, PROMPT_USER, v)
            t0 = time.perf_counter()
            try:
                resp = await client.post(settings.base_url.rstrip("/") + path, json=body, headers=headers)
                ms = (time.perf_counter() - t0) * 1000
                text = ""
                if resp.status_code == 200:
                    try:
                        text = foundry.parse(family, v["stream"], resp.content, resp.headers.get("content-type", ""))
                    except (KeyError, IndexError, TypeError, ValueError):
                        text = "(200, but unparseable)"
                mark = "✓" if resp.status_code == 200 and text.strip() else "✗"
                print(f"  {mark} {v['name']:<40} {resp.status_code}  {ms:6.0f} ms  {text.strip()[:60]!r}")
            except Exception as e:  # noqa: BLE001 - report and keep probing other variants
                print(f"  ✗ {v['name']:<40} {type(e).__name__}: {secrets_store.redact(str(e))[:80]}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Probe an LLM endpoint (token asked interactively).")
    ap.add_argument("--provider", choices=["foundry", "openrouter"], default="foundry")
    ap.add_argument("--model", default="azure:gpt-4.1-mini",
                    help="Foundry: family:id, e.g. azure:gpt-4.1-mini. OpenRouter: a slug, e.g. openai/gpt-4.1-mini")
    ap.add_argument("--project", default=FOUNDRY_DEFAULT_PROJECT, help="Foundry project suffix")
    ap.add_argument("--base-url", default=FOUNDRY_BASE_URL)
    ap.add_argument("--ca-bundle", default=None, help="Path to a corporate CA bundle (or set LLM_CA_BUNDLE)")
    ap.add_argument("--each-variant", action="store_true", help="Foundry only: try every endpoint variant separately")
    ap.add_argument("--list", action="store_true", help="List the Foundry model catalogue and exit")
    args = ap.parse_args()

    if args.list:
        for m in FOUNDRY_MODELS:
            print(f"  {m['ref']:<40} cost {m['cost']}")
        return 0

    token = getpass.getpass("Paste token (input hidden): ").strip()
    if not token:
        print("No token entered.")
        return 1
    secrets_store.set(token)                    # only so error text can be redacted; memory only
    settings = llm.Settings(provider=args.provider, project=args.project, base_url=args.base_url,
                            ca_bundle=args.ca_bundle)
    print(f"Probing {args.provider} · {args.model}")
    if args.each_variant and args.provider == "foundry":
        asyncio.run(each_variant(args.model, token, settings))
        return 0
    return asyncio.run(probe(args.provider, args.model, token, settings))


if __name__ == "__main__":
    sys.exit(main())
