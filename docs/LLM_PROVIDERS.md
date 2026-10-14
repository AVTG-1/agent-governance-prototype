# LLM providers, request shapes and model recommendations

The app talks to models through **one small module**, `app/llm/`. It exposes:

```python
async def complete(role: str, system: str, user: str, *, json_mode: bool = True) -> LLMResult
async def test_model(provider, model_ref, token, settings) -> TestResult   # used by the connection gate
```

`LLMResult` holds `text`, `latency_ms`, `model_ref` and `usage` (if returned). There is no plugin system: just one function per request family below.

> **Tokens:** examples use `<YOUR_FOUNDRY_TOKEN>`. Real tokens are pasted by the presenter into the connection screen, held in memory, and never written anywhere. Any token in old notes is expired. Do not copy one.

## 1. LLM Foundry (default and recommended)

- **Base URL:** `https://llmfoundry.straive.com`. Configurable in the connection screen's *Advanced* section; not a secret.
- **Auth header:** `Authorization: Bearer <YOUR_FOUNDRY_TOKEN>:<project>`, where `<project>` defaults to `llmproxy-playground`. If the pasted token already contains a `:` followed by text, send it unchanged.
- **Reachable only from the presenter's work laptop.** Claude Code cannot call it. Build to these shapes and test with the mock.

Foundry exposes four request families. A model is referenced as `family:id`, for example `azure:gpt-4.1-mini`.

### 1.1 `azure`: Azure OpenAI deployments (OpenAI chat format, no `model` field)

```
POST {base}/azure/openai/deployments/{deployment}/chat/completions?api-version=2025-01-01-preview
{"messages":[{"role":"system","content":"…"},{"role":"user","content":"…"}],
 "temperature":0, "stream":false, "response_format":{"type":"json_object"}}
```

- Read `choices[0].message.content`.
- The Foundry examples use `"stream": true`. Use `false` for simplicity. If the proxy rejects non-streaming, fall back to streaming and concatenate `choices[0].delta.content` from the SSE `data:` lines.
- If `response_format` is rejected (400), retry once without it. The prompt already demands JSON.

### 1.2 `openai`: public OpenAI models (OpenAI chat format with `model`)

```
POST {base}/openai/v1/chat/completions
{"model":"gpt-5-mini","messages":[…],"stream":false}
```

- For `gpt-5`, `gpt-5-mini` and `gpt-5-nano`, **omit `temperature`**: these models only accept the default (the Foundry examples send 1). `gpt-5.1` accepts 0.

### 1.3 `bedrock`: Anthropic Claude and Amazon Nova (Bedrock Converse format)

```
POST {base}/bedrock/{modelId}/converse            ← try first (non-streaming)
POST {base}/bedrock/{modelId}/converse_stream     ← documented by Foundry; fallback
{"system":[{"text":"…"}],
 "messages":[{"role":"user","content":[{"text":"…"}]}],
 "inferenceConfig":{"temperature":0,"maxTokens":1500}}
```

- **Non-streaming:** read `output.message.content[*].text`.
- **Streaming fallback:** the body may be AWS event-stream binary or SSE, depending on the proxy. Robust approach: decode as UTF-8 with `errors="ignore"`, extract every JSON object containing `"contentBlockDelta"` (or `"delta"`), and concatenate `delta.text`. Keep this parser in one small function with a unit test that uses a captured-style sample.
- `scripts/probe_llm.py` must report which of the two endpoints worked, so the presenter knows.

### 1.4 `gemini`: Google Gemini (generateContent format)

```
POST {base}/gemini/v1beta/models/{model}:generateContent                    ← try first
POST {base}/gemini/v1beta/models/{model}:streamGenerateContent?alt=sse       ← documented; fallback
{"system_instruction":{"parts":[{"text":"…"}]},
 "contents":[{"role":"user","parts":[{"text":"…"}]}],
 "generationConfig":{"temperature":0,"responseMimeType":"application/json"}}
```

- **Non-streaming:** read `candidates[0].content.parts[*].text`.
- **SSE fallback:** parse each `data:` line as JSON and concatenate the same path.
- If `responseMimeType` is rejected, retry without it.

### 1.5 Foundry model catalogue (from the Foundry listing)

The cost figure is the tag from the Foundry listing, shown as-is in the model picker. It is likely USD per million input tokens; confirm on the Foundry portal.

| Family | Model ref | Endpoint id | Cost tag |
|---|---|---|---|
| azure | `azure:gpt-4.1` | `gpt-4.1` | 2.0 |
| azure | `azure:gpt-4.1-mini` | `gpt-4.1-mini` | 0.4 |
| azure | `azure:gpt-4.1-nano` | `gpt-4.1-nano` | 0.1 |
| azure | `azure:gpt-4o` | `gpt-4o` | 5 |
| azure | `azure:gpt-4o-mini` | `gpt-4o-mini` | 0.15 |
| azure | `azure:gpt-5.1` | `gpt-5.1` | 1.25 |
| azure | `azure:gpt-5.4` | `gpt-5.4` | 2.5 |
| azure | `azure:gpt-5.4-mini` | `gpt-5.4-mini` | 0.75 |
| azure | `azure:gpt-5.4-nano` | `gpt-5.4-nano` | 0.2 |
| azure | `azure:o1-mini` | `o1-mini` | 5 |
| openai | `openai:gpt-5` | `gpt-5` | 1.25 |
| openai | `openai:gpt-5-mini` | `gpt-5-mini` | 0.25 |
| openai | `openai:gpt-5-nano` | `gpt-5-nano` | 0.05 |
| openai | `openai:gpt-5.1` | `gpt-5.1` | 1.25 |
| bedrock | `bedrock:claude-haiku-4.5` | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | 1.0 |
| bedrock | `bedrock:claude-sonnet-4.5` | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | 3.0 |
| bedrock | `bedrock:claude-sonnet-4` | `us.anthropic.claude-sonnet-4-20250514-v1:0` | 3.0 |
| bedrock | `bedrock:claude-opus-4.5` | `global.anthropic.claude-opus-4-5-20251101-v1:0` | 5.0 |
| bedrock | `bedrock:claude-opus-4.1` | `us.anthropic.claude-opus-4-1-20250805-v1:0` | 16.0 |
| bedrock | `bedrock:nova-pro` | `amazon.nova-pro-v1:0` | 0.8 |
| bedrock | `bedrock:nova-lite` | `amazon.nova-lite-v1:0` | 0.06 |
| bedrock | `bedrock:nova-micro` | `amazon.nova-micro-v1:0` | 0.035 |
| gemini | `gemini:gemini-2.5-flash-lite` | `gemini-2.5-flash-lite` | 0.1 |
| gemini | `gemini:gemini-2.5-flash` | `gemini-2.5-flash` | 0.3 |
| gemini | `gemini:gemini-2.5-pro` | `gemini-2.5-pro` | 2.5 |
| gemini | `gemini:gemini-3-flash-preview` | `gemini-3-flash-preview` | 0.5 |
| gemini | `gemini:gemini-3.1-flash-lite-preview` | `gemini-3.1-flash-lite-preview` | 0.25 |
| gemini | `gemini:gemini-3.1-pro-preview` | `gemini-3.1-pro-preview` | 2.0 |

Keep this table as data in `app/llm/catalog.py`. The model picker reads from it and also accepts a custom `family:id`.

## 2. OpenRouter (alternative)

```
POST https://openrouter.ai/api/v1/chat/completions
Authorization: Bearer <YOUR_OPENROUTER_KEY>
HTTP-Referer: http://localhost   (optional)    X-Title: Agent governance demo (optional)
{"model":"openai/gpt-4.1-mini","messages":[…],"temperature":0,"response_format":{"type":"json_object"}}
```

- This uses the same parser as §1.1.
- Suggested slugs: `openai/gpt-4.1-mini` (agent) and `anthropic/claude-sonnet-4.5` (investigator). Slugs change, so verify them on openrouter.ai/models and allow a custom slug in the picker.

## 3. Model recommendations for this demo

There are only two LLM roles, and **neither ever makes an access decision**.

| Role | What it must do | Recommended (Foundry) | Good alternatives | Avoid, and why |
|---|---|---|---|---|
| **Agent**: the reconciliation agent that gets fooled | Produce a small, valid JSON tool plan fast; follow operational notes the way a naive legacy agent would | **`azure:gpt-4.1-mini`**: fast, cheap, reliable JSON, accepts temperature 0 for repeatable runs | `azure:gpt-4o-mini` (cheaper, a little more likely to follow the injected note); `azure:gpt-4.1` (most reliable JSON) | Claude models: strong prompt-injection resistance means they often refuse, which triggers the recorded-plan fallback more often. gpt-5 family: fixed temperature and reasoning latency make runs less repeatable. |
| **Investigator**: writes the case and drafts a narrower policy | Reason over a short event log; return a clear 4-sentence narrative and a schema-valid diff; respect "only narrow" instructions | **`bedrock:claude-sonnet-4.5`**: strong reasoning and clear writing, on the "safe-private" route | `azure:gpt-5.1` (temperature 0 supported); `gemini:gemini-3-flash-preview` (fast, cheap) | Opus 4.1 (cost 16, slow for live use); nano, micro and lite models (weak at the diff); o1-mini (slow, no system prompt) |

- **OpenRouter equivalents:** agent `openai/gpt-4.1-mini`; investigator `anthropic/claude-sonnet-4.5`.
- **Cost of one run:** 3 live calls (agent plan, investigator case, investigator diff) plus 2 connection tests, a few thousand tokens in total. That is well under one US dollar at the listed rates.
- **Rehearse with the exact pair you will present with.** The agent role is deliberately sensitive to model choice. If your chosen agent model resists the injection in rehearsal, the recorded-plan fallback (SPEC §5.4) keeps the story honest. That is a talking point, not a failure.

## 4. Networking on the work laptop

- Use one `httpx.AsyncClient` with `trust_env=True` (honours `HTTPS_PROXY` and `NO_PROXY`) and a 30 s timeout.
- Optional non-secret setting `LLM_CA_BUNDLE`, read from an environment variable or the *Advanced* section: a path to a corporate CA bundle passed as `verify=`. Never disable TLS verification.
- Errors shown to the presenter: 401/403 → "Token rejected or expired. Paste a fresh token." Timeout → "No response in 30 s. Check VPN or proxy." 404 → "Model or endpoint not found on this gateway."

## 5. `scripts/probe_llm.py` (presenter tool, run on the work laptop)

```
python scripts/probe_llm.py --provider foundry --model azure:gpt-4.1-mini
python scripts/probe_llm.py --provider foundry --model bedrock:claude-sonnet-4.5
python scripts/probe_llm.py --provider openrouter --model openai/gpt-4.1-mini
```

- It prompts for the token with `getpass` (never as an argument and never from a file).
- It sends "Reply with the JSON {\"ok\": true}", then prints status, latency, the endpoint variant that worked (non-stream or stream) and the parsed reply.
