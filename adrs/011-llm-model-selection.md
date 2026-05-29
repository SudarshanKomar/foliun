# ADR-011: Use GPT-4o-mini as Primary LLM with E2B Gemma 4 as Alternative

> **⚠ SUPERSEDED**: This ADR has been superseded by [ADR-013: Switch from E2B to Ollama (Gemma 4 2B) for Local LLM](013-switch-from-e2b-to-ollama.md). E2B was found to be unsuitable because it is a cloud service (not local/private), does not provide free APIs, and does not meet the project's privacy requirements. Ollama with Gemma 4 2B replaces E2B as the local LLM option.

## Status
Superseded by [ADR-013](013-switch-from-e2b-to-ollama.md)

## Context
The system requires LLM capabilities for two distinct operations:
1. **Query rewriting**: Generating 3 semantically diverse query variants from the user's original query
2. **Answer synthesis**: Generating grounded answers with citations from retrieved context

The LLM must support streaming output, handle ~4000 tokens of context plus system prompt, and produce reliable structured responses (citations in `[Doc: title, Page: N]` format). Cost control is important for a Phase 1 learning project.

Candidates considered: GPT-4o, GPT-4o-mini, Claude 3 Haiku, Gemma 4 (self-hosted), Gemma 4 via E2B.

## Decision
We will use **GPT-4o-mini** as the primary LLM and **Gemma 4 via E2B sandbox** as a cost-control alternative.

- GPT-4o-mini: used for both query rewriting and answer synthesis by default
- Gemma 4 via E2B: user-selectable alternative at query time via `model` parameter
- Both accessed via API (OpenAI SDK and E2B SDK respectively)
- Streaming enabled for answer synthesis; non-streaming for query rewriting

**Critical clarification**: E2B is a **cloud sandbox service**, not local execution. Data is sent to E2B infrastructure. This is a cost-control alternative, **not** a privacy-preserving option.

## Consequences

### Positive
- GPT-4o-mini: fast (~1s first token), cheap ($0.15/1M input, $0.60/1M output), 128K context
- E2B alternative provides cost flexibility without self-hosting infrastructure
- Streaming via OpenAI SDK is well-documented and reliable
- GPT-4o-mini excels at instruction following — critical for structured citation format
- Model selection at query time allows experimentation with different models

### Negative
- Hard dependency on OpenAI API for primary path — no offline operation
- E2B is also a cloud service — both options require internet connectivity
- GPT-4o-mini occasionally hallucinates citations despite grounding prompts (mitigated by post-validation)
- No true local/private LLM option in Phase 1

### Neutral
- Self-hosted LLM via Ollama is deferred to Phase 2 for true privacy
- E2B availability is an external dependency; fallback to GPT-4o-mini if E2B is unreachable
- Query rewriting uses non-streaming calls since the full response is needed before retrieval

## Related ADRs
- ADR-008: Use Server-Sent Events for response streaming
- ADR-012: Remove general knowledge fallback
