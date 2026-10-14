"""Bug (a): a pasted token with a stray character must never crash the gate or reach a header."""
import asyncio

import pytest

from app import secrets_store
from tests.conftest import pass_gate

MODELS = {"agent": "azure:gpt-4.1-mini", "investigator": "bedrock:claude-sonnet-4.5"}
NOT_SENDABLE = "The token contains a character that can't be sent. Paste it again from the source."


def test_whitespace_and_invisible_characters_are_stripped():
    assert secrets_store.clean(" fake-abc\n-def​﻿\t  ") == "fake-abc-def"


@pytest.mark.parametrize("bad", ["fake·token-1234", "fake•token-1234", "fake-tokén-1234"])
def test_non_ascii_is_refused(bad):
    with pytest.raises(ValueError, match="can't be sent"):
        secrets_store.clean(bad)


def test_pasted_token_with_middle_dot_bullet_newline_and_space_gets_a_plain_400(client):
    r = client.post("/api/connection/test", json={"provider": "foundry", "token": "fake-·tok•en\n-5678 ",
                                                    "project": "llmproxy-playground", "models": MODELS})
    assert r.status_code == 400
    assert r.json()["detail"] == NOT_SENDABLE
    assert secrets_store.get() is None                       # nothing stored
    assert client.post("/api/demo/start").status_code == 409


def test_newline_and_trailing_space_alone_are_cleaned_and_pass(client):
    r = client.post("/api/connection/test", json={"provider": "foundry", "token": "fake-gate\n-token-0009 ",
                                                    "project": " llmproxy-playground\n", "models": MODELS})
    assert r.status_code == 200 and r.json()["ready"]
    assert secrets_store.get() == "fake-gate-token-0009"
    assert r.json()["project"] == "llmproxy-playground"


def test_suffix_with_a_stray_character_is_refused(client):
    r = client.post("/api/connection/test", json={"provider": "foundry", "token": "fake-gate-token-0010",
                                                    "project": "llmproxy·playground", "models": MODELS})
    assert r.status_code == 400 and "suffix" in r.json()["detail"]


def test_masked_display_value_sent_back_keeps_the_stored_token(client):
    pass_gate(client, fake="fake-gate-token-abcd")
    masked = client.get("/api/connection/status").json()["token"]
    r = client.post("/api/connection/test", json={"provider": "foundry", "token": masked,
                                                    "project": "llmproxy-playground", "models": MODELS})
    assert r.status_code == 200 and r.json()["ready"]
    assert secrets_store.get() == "fake-gate-token-abcd"
    assert client.post("/api/connection/token", json={"token": masked}).status_code == 400


def test_mid_demo_token_with_a_stray_character_is_a_400(client):
    r = client.post("/api/connection/token", json={"token": "fake·token\n"})
    assert r.status_code == 400 and r.json()["detail"] == NOT_SENDABLE


def test_header_encoding_error_becomes_a_plain_message():
    """Safety net: even if a non-ASCII value reached the HTTP layer, the gate gets words, not a 500."""
    import app.llm as llm

    class Boom:
        async def post(self, *a, **k):
            raise UnicodeEncodeError("ascii", "\xb7", 0, 1, "ordinal not in range(128)")

    with pytest.raises(llm.LLMError) as e:
        asyncio.run(llm._try_variants(Boom(), "foundry", "azure", "https://x.invalid", {}, [{"name": "v"}],
                                      lambda v: ("/p", {}), "k", "azure:gpt-4.1-mini"))
    assert e.value.message == NOT_SENDABLE
