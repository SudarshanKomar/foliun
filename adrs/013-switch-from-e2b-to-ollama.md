# ADR-013: Switch from E2B to Ollama (Gemma 4 2B) for Local LLM

## Status
Accepted

## Context
ADR-011 established GPT-4o-mini as the primary LLM and Gemma 4 via E2B sandbox as a cost-control alternative. During implementation planning, several critical issues with the E2B approach were identified:

1. **E2B is not local or private**: E2B is a cloud sandbox service. All document context and queries are sent to E2B infrastructure for processing. This was already flagged in ADR-011 and the system overview, but the mitigation ("defer local LLM to Phase 2") is insufficient given the project's privacy requirements.
2. **E2B does not provide free cloud APIs**: The cost-control rationale for E2B is undermined by the fact that E2B itself requires a paid API. This removes the primary justification for choosing E2B over simply using GPT-4o-mini exclusively.
3. **Privacy requirement**: Users upload sensitive research documents. Sending document content to E2B infrastructure (in addition to OpenAI) expands the data exposure surface unnecessarily. A true local option keeps sensitive data on the user's own infrastructure.
4. **Ollama provides actual local execution**: Ollama runs LLMs locally on the user's machine. Data never leaves the infrastructure. It is free to run (hardware cost only) and supports Gemma 4 2B.
5. **Gemma 4 2B is lightweight**: The 2B parameter model can run on almost all low-end machines (4GB+ RAM, no GPU required), making it accessible without specialized hardware.

The system overview already noted in its assumptions: "For true local/private execution, a self-hosted model (e.g., Ollama) would be required." This ADR accelerates that plan from Phase 2 to Phase 1.

## Decision
We will **replace E2B with Ollama** for the local/alternative LLM option.

- **Ollama** runs **Gemma 4 2B** locally on the user's infrastructure at `localhost:11434`
- Data **never leaves the user's infrastructure** when using Ollama
- **GPT-4o-mini** remains the primary LLM (cloud, OpenAI API)
- User can select model at query time via the `model` parameter:
  - `"gpt-4o-mini"` (default): OpenAI API — cloud, requires internet
  - `"gemma-4-2b"`: Ollama — local, private, no internet required
- Ollama exposes an OpenAI-compatible API (`/v1/chat/completions`), simplifying integration
- Streaming is supported via Ollama's API (SSE-compatible chunked responses)
- `E2B_API_KEY` environment variable is replaced with `OLLAMA_BASE_URL` (default: `http://localhost:11434`)

## Consequences

### Positive
- **True privacy**: Document context and queries never leave the user's infrastructure when using Ollama
- **Zero API cost**: Ollama is free to run — only hardware cost (electricity)
- **Runs on low-end machines**: Gemma 4 2B requires ~4GB RAM, no GPU needed
- **OpenAI-compatible API**: Ollama supports `/v1/chat/completions` endpoint, minimizing integration code changes
- **Open-source**: Both Ollama and Gemma 4 are open-source
- **Offline operation**: Ollama works without internet connectivity (unlike both OpenAI and E2B)
- **Local control**: Full control over model version, configuration, and resource allocation

### Negative
- **Requires local setup**: User must install Ollama and pull the Gemma 4 2B model before use
- **Hardware resources**: Gemma 4 2B uses ~4GB RAM while running (but this is minimal compared to larger models)
- **Lower quality than GPT-4o-mini**: 2B parameter model has significantly less capability than GPT-4o-mini for instruction following, citation formatting, and complex synthesis
- **Ollama must be running**: The Ollama service must be started separately (not managed by the RAG application)
- **Cold start latency**: First inference after model load may be slower (~2-5 seconds)

### Neutral
- Fallback to GPT-4o-mini if Ollama is unavailable (same pattern as E2B fallback)
- Operational overhead shifts from managing E2B API key to managing local Ollama installation
- Model management (pulling, updating Gemma 4 2B) is the user's responsibility
- Integration complexity is similar — Ollama's OpenAI-compatible API may actually be simpler than E2B SDK

## Related ADRs
- ADR-011: Superseded by this ADR (ADR-013)
- ADR-008: Use Server-Sent Events for response streaming (unchanged — Ollama supports streaming)
- ADR-012: Remove general knowledge fallback (unchanged — still applies regardless of LLM choice)
