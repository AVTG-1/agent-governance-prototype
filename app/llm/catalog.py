"""Model catalogue, from docs/LLM_PROVIDERS.md. The cost tag is shown as-is from the Foundry listing."""
from __future__ import annotations

# (family, short id, endpoint id, cost tag)
_FOUNDRY = [
    ("azure", "gpt-4.1", "gpt-4.1", "2.0"),
    ("azure", "gpt-4.1-mini", "gpt-4.1-mini", "0.4"),
    ("azure", "gpt-4.1-nano", "gpt-4.1-nano", "0.1"),
    ("azure", "gpt-4o", "gpt-4o", "5"),
    ("azure", "gpt-4o-mini", "gpt-4o-mini", "0.15"),
    ("azure", "gpt-5.1", "gpt-5.1", "1.25"),
    ("azure", "gpt-5.4", "gpt-5.4", "2.5"),
    ("azure", "gpt-5.4-mini", "gpt-5.4-mini", "0.75"),
    ("azure", "gpt-5.4-nano", "gpt-5.4-nano", "0.2"),
    ("azure", "o1-mini", "o1-mini", "5"),
    ("openai", "gpt-5", "gpt-5", "1.25"),
    ("openai", "gpt-5-mini", "gpt-5-mini", "0.25"),
    ("openai", "gpt-5-nano", "gpt-5-nano", "0.05"),
    ("openai", "gpt-5.1", "gpt-5.1", "1.25"),
    ("bedrock", "claude-haiku-4.5", "us.anthropic.claude-haiku-4-5-20251001-v1:0", "1.0"),
    ("bedrock", "claude-sonnet-4.5", "us.anthropic.claude-sonnet-4-5-20250929-v1:0", "3.0"),
    ("bedrock", "claude-sonnet-4", "us.anthropic.claude-sonnet-4-20250514-v1:0", "3.0"),
    ("bedrock", "claude-opus-4.5", "global.anthropic.claude-opus-4-5-20251101-v1:0", "5.0"),
    ("bedrock", "claude-opus-4.1", "us.anthropic.claude-opus-4-1-20250805-v1:0", "16.0"),
    ("bedrock", "nova-pro", "amazon.nova-pro-v1:0", "0.8"),
    ("bedrock", "nova-lite", "amazon.nova-lite-v1:0", "0.06"),
    ("bedrock", "nova-micro", "amazon.nova-micro-v1:0", "0.035"),
    ("gemini", "gemini-2.5-flash-lite", "gemini-2.5-flash-lite", "0.1"),
    ("gemini", "gemini-2.5-flash", "gemini-2.5-flash", "0.3"),
    ("gemini", "gemini-2.5-pro", "gemini-2.5-pro", "2.5"),
    ("gemini", "gemini-3-flash-preview", "gemini-3-flash-preview", "0.5"),
    ("gemini", "gemini-3.1-flash-lite-preview", "gemini-3.1-flash-lite-preview", "0.25"),
    ("gemini", "gemini-3.1-pro-preview", "gemini-3.1-pro-preview", "2.0"),
]
FAMILY_LABEL = {"azure": "Azure OpenAI", "openai": "OpenAI", "bedrock": "Bedrock", "gemini": "Gemini"}

FOUNDRY_MODELS = [
    {"ref": f"{fam}:{short}", "family": fam, "endpoint_id": eid, "cost": cost,
     "label": f"{short} · {FAMILY_LABEL[fam]} · cost {cost}"}
    for fam, short, eid, cost in _FOUNDRY
]
# Models that only accept the default temperature.
FIXED_TEMPERATURE = {"gpt-5", "gpt-5-mini", "gpt-5-nano", "o1-mini"}
NO_SYSTEM_ROLE = {"o1-mini"}

OPENROUTER_MODELS = [
    {"ref": "openai/gpt-4.1-mini", "label": "openai/gpt-4.1-mini"},
    {"ref": "openai/gpt-4o-mini", "label": "openai/gpt-4o-mini"},
    {"ref": "openai/gpt-4.1", "label": "openai/gpt-4.1"},
    {"ref": "anthropic/claude-sonnet-4.5", "label": "anthropic/claude-sonnet-4.5"},
    {"ref": "google/gemini-2.5-flash", "label": "google/gemini-2.5-flash"},
]

RECOMMENDED = {
    "foundry": {"agent": "azure:gpt-4.1-mini", "investigator": "bedrock:claude-sonnet-4.5"},
    "openrouter": {"agent": "openai/gpt-4.1-mini", "investigator": "anthropic/claude-sonnet-4.5"},
}


def resolve_foundry(ref: str) -> tuple[str, str]:
    """'family:id' -> (family, endpoint id). Accepts catalogue refs and custom 'family:endpoint-id'."""
    for m in FOUNDRY_MODELS:
        if m["ref"] == ref:
            return m["family"], m["endpoint_id"]
    family, _, rest = ref.partition(":")
    if family not in FAMILY_LABEL or not rest:
        raise ValueError(f"Model must look like family:id with family one of {', '.join(FAMILY_LABEL)}.")
    return family, rest


def short_name(ref: str) -> str:
    """Display name: 'azure:gpt-4.1-mini' -> 'gpt-4.1-mini', 'anthropic/claude-sonnet-4.5' -> 'claude-sonnet-4.5'."""
    return ref.split(":", 1)[-1].split("/")[-1] if ":" in ref.split("/")[0] else ref.split("/")[-1]
