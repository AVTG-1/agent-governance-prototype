"""Non-secret settings only. Tokens never live here (see secrets_store.py)."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"
DATA_DIR = ROOT / "app" / "estate" / "data"
PROMPTS_DIR = ROOT / "app" / "prompts"

HOST = "127.0.0.1"
PORT = 8765

FOUNDRY_BASE_URL = "https://llmfoundry.straive.com"
FOUNDRY_DEFAULT_PROJECT = "llmproxy-playground"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
LLM_TIMEOUT_S = 30.0


def ca_bundle() -> str | None:
    """Optional corporate CA bundle path (a path, not a secret)."""
    value = os.environ.get("LLM_CA_BUNDLE", "").strip()
    return value or None
