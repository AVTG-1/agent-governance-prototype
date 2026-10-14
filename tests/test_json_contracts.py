"""Bug (b): every LLM contract survives fences, prose, trailing commas and cut-off replies, says plainly
what went wrong, retries once with the reason, and prints the raw reply to the terminal for diagnosis."""
import asyncio
import json

import pytest

import app.llm as llm
from app.core import rulebook as rb
from app.llm import ContractError, LLMResult, extract_json, foundry, parse_contract
from app.llm.mock import RULEBOOK

GOOD = json.dumps(RULEBOOK)


def test_fenced():
    assert extract_json(f"```json\n{GOOD}\n```") == RULEBOOK
    assert extract_json(f"Here you go:\n```\n{GOOD}\n```\nLet me know.") == RULEBOOK


def test_prose_wrapped():
    assert extract_json(f"Sure! Based on the summary, here is the draft rulebook: {GOOD} I hope this helps.") == RULEBOOK


def test_trailing_commas():
    t = '{"grants": [{"agent": "kyc-agent", "capability": "refdata.read", "tags": [],},], "flags": [],}'
    assert extract_json(t)["grants"][0]["capability"] == "refdata.read"


def test_braces_and_commas_inside_strings_are_left_alone():
    t = '{"a": "x}, ]", "b": "say \\"{hi}\\","}'
    assert extract_json(t) == {"a": "x}, ]", "b": 'say "{hi}",'}


def test_truncated_is_reported_as_cut_off():
    with pytest.raises(ContractError) as e:
        extract_json(GOOD[: len(GOOD) // 2])
    assert e.value.truncated and "cut off" in str(e.value)


def test_provider_stop_reason_marks_a_reply_as_cut_off():
    r = LLMResult('{"grants": [{"agent": "kyc-agent", "capability": "x"', 5, "bedrock:claude-sonnet-4.5",
                  stop_reason="max_tokens")
    with pytest.raises(ContractError) as e:
        parse_contract(r, rb.RulebookDraft)
    assert e.value.truncated


@pytest.mark.parametrize("body", [
    b'{"choices":[{"message":{"content":"{"},"finish_reason":"length"}]}',
    b'data: {"choices":[{"delta":{},"finish_reason":"length"}]}\n\ndata: [DONE]',
    b'{"output":{"message":{"content":[{"text":"{"}]}},"stopReason":"max_tokens"}',
    b'\x00\x00:event-type\x07messageStop{"stopReason":"max_tokens"}',
    b'{"candidates":[{"content":{"parts":[{"text":"{"}]},"finishReason":"MAX_TOKENS"}]}',
])
def test_stop_reason_detected_for_every_family(body):
    assert foundry.stop_reason(body) == "max_tokens"


def test_normal_stop_is_not_cut_off():
    assert foundry.stop_reason(b'{"choices":[{"finish_reason":"stop"}]}') is None
    assert foundry.stop_reason(b'{"stopReason":"end_turn"}') is None


def test_output_budget_is_large_enough_and_json_mode_is_on():
    _, body = foundry.azure_request("gpt-4.1-mini", "S", "U")
    assert body["response_format"] == {"type": "json_object"} and body["max_tokens"] >= 4096
    assert foundry.bedrock_request("m", "S", "U")[1]["inferenceConfig"]["maxTokens"] >= 4096
    assert foundry.openai_request("gpt-5-mini", "S", "U")[1]["max_completion_tokens"] >= 8000
    assert foundry.gemini_request("g", "S", "U")[1]["generationConfig"]["maxOutputTokens"] >= 8000


def test_compact_rulebook_contract_is_small():
    """ids and short codes, no prose: the whole good draft is well under the output budget."""
    assert len(GOOD) < 3000                    # ~ 800 tokens against a 4,096-token budget
    draft = rb.RulebookDraft.model_validate(RULEBOOK)
    assert draft.grants[5].evidence == "calendar" and draft.flags[0].issue == "breaks R-EGR-01"


class Replies:
    """A fake provider seam that returns the given texts in order and records each user prompt."""

    def __init__(self, *texts, stop=None):
        self.texts, self.stop, self.users = list(texts), stop, []

    async def __call__(self, provider, model_ref, token, settings, system, user, json_mode=True):
        self.users.append(user)
        return LLMResult(self.texts.pop(0), 5, model_ref, None, "fake", self.stop)


@pytest.fixture
def seam(monkeypatch):
    from app import secrets_store
    secrets_store.set("fake-contract-token-0001")
    yield lambda fake: monkeypatch.setattr(llm, "_call_model", fake)
    secrets_store.clear()


def test_retry_once_with_the_parse_error_appended(seam, capsys):
    fake = Replies('{"grants": [{"agent": "kyc-agent" "capability": "refdata.read"}]}', GOOD)
    seam(fake)
    draft, r = asyncio.run(llm.complete_json("investigator", "S", "U", rb.RulebookDraft, job="rulebook draft"))
    assert len(draft.grants) == 16 and len(fake.users) == 2
    assert "Expecting ',' delimiter" in fake.users[1] and "Return only the JSON object" in fake.users[1]
    err = capsys.readouterr().err
    assert "rulebook draft: unusable reply" in err and '"kyc-agent" "capability"' in err   # raw output printed
    assert "fake-contract-token-0001" not in err


def test_two_cut_off_replies_say_so(seam):
    seam(Replies('{"grants": [', '{"grants": [{"agent"', stop="max_tokens"))
    with pytest.raises(llm.LLMError) as e:
        asyncio.run(llm.complete_json("investigator", "S", "U", rb.RulebookDraft, job="rulebook draft"))
    assert e.value.kind == "parse" and "cut off at the output limit" in e.value.message
    assert "rulebook draft" in e.value.message


def test_schema_error_is_named(seam):
    seam(Replies('{"grants": []}', '{"grants": []}'))
    with pytest.raises(llm.LLMError) as e:
        asyncio.run(llm.complete_json("investigator", "S", "U", rb.RulebookDraft, job="rulebook draft"))
    assert "unusable JSON twice" in e.value.message and "grants" in e.value.message
