# Free AI Providers for the Clinical Assistant

The Clinical Assistant explains official ICU recommendations and authorized patient
information in plain language. It **never** decides clinical outcomes — the deterministic
ICU Recommendation Engine remains the authoritative component.

The assistant needs a chat-completions LLM behind it. This document lists **free
providers** whose standing free tiers are far above the project requirement of
"at least ~20 messages per day", and explains how to configure them.

## Recommendation

| Priority | Provider | Why |
| --- | --- | --- |
| Primary | **Groq** | No credit card. ~30 req/min and ~1,000 requests/day on production models (e.g. `openai/gpt-oss-120b`), extremely fast inference. |
| Fallback | **Google Gemini** | No credit card. ~10 req/min, ~250–1,500 requests/day depending on model. Different infrastructure, so a Groq outage/rate limit never takes the assistant down. |

Configuring **Groq + Gemini together** means no single provider's daily quota can make
the assistant unavailable — exactly the resilience needed for a hospital tool.

## Free tier snapshot (August 2026)

Verify current limits on each provider's console; free tiers change over time.

| Provider | Free limits (approx.) | Credit card | Key console |
| --- | --- | --- | --- |
| Groq | 30 req/min · ~1,000 req/day · ~500K tokens/day | No | https://console.groq.com |
| Google Gemini | 10–15 req/min · ~250–1,500 req/day | No | https://aistudio.google.com |
| Cerebras | ~1M tokens/day | No | https://cloud.cerebras.ai |
| Mistral | ~1B tokens/month | No | https://console.mistral.ai |
| SambaNova | 20 req/min · ~200K tokens/day per model | No | https://cloud.sambanova.ai |
| OpenRouter | 20 req/min · 50 req/day (1,000/day after a one-time $10 top-up) | No | https://openrouter.ai |
| DeepSeek (legacy) | Pay-as-you-go (very cheap, not free) | Yes | https://platform.deepseek.com |

Even the smallest genuinely-free quota here (OpenRouter, 50/day) is 2.5× the project's
20-messages-per-day floor.

## Configuration

All providers expose an **OpenAI-compatible** `/chat/completions` endpoint, so switching
providers requires no code changes — only environment variables:

```bash
# Primary provider (Groq recommended free default)
AI_PROVIDER=groq
GROQ_API_KEY=gsk_...            # from console.groq.com/keys
# AI_MODEL=openai/gpt-oss-120b  # optional override

# Optional automatic failover (used on 429 / 5xx / timeout)
AI_FALLBACK_PROVIDER=gemini
GEMINI_API_KEY=AIza...          # from aistudio.google.com
# AI_FALLBACK_MODEL=gemini-2.5-flash
```

Resolution rules:

1. `AI_PROVIDER` explicitly selects the provider.
2. Otherwise the first provider-specific key found (`GROQ_API_KEY`, `GEMINI_API_KEY`,
   `OPENROUTER_API_KEY`, `CEREBRAS_API_KEY`, `MISTRAL_API_KEY`, `SAMBANOVA_API_KEY`)
   selects it automatically.
3. A legacy `DEEPSEEK_API_KEY` still selects DeepSeek, so existing deployments behave
   exactly as before.
4. With no key at all, the assistant returns a deterministic fallback message and the
   ICU Recommendation System continues to work normally.

A generic `AI_API_KEY` variable is also honoured for any provider, which is handy for
PaaS-style secret injection where you cannot add provider-specific variable names.

## Architecture safety rules (unchanged)

- The ICU Recommendation Engine is deterministic and **never** calls the LLM.
- The assistant only receives the context the current user is authorized to see
  (guardian views are strictly filtered).
- Every assistant answer passes the safety validator and is audit-logged, including
  the provider that produced it.
- Provider failures degrade to a fixed fallback message; conversations never block
  clinical workflows.

## Implementation reference

- `backend/apps/clinical_assistant/services/llm_service.py` — provider registry,
  failover chain, graceful fallback.
- `backend/apps/clinical_assistant/services/deepseek_service.py` — backwards-compatible
  facade over the new service.
- `.env.example` — documented environment variables.
