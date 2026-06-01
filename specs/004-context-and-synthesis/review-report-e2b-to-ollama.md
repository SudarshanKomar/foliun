# Review Report: 004-context-and-synthesis (E2B → Ollama Migration)

## Change Triggered By
- **ADR-013**: Switch from E2B to Ollama (Gemma 4 2B) for Local LLM
- Supersedes ADR-011

## Impact Assessment
- **Severity**: High — this spec has the most E2B references of any spec (primary LLM integration point)
- **Scope**: spec.md (FR-5, NFR-5, failure cases, success criteria), plan.md (LLM synthesis flow, error handling), tasks.md (E2B SDK tasks, fallback tasks, tests), notes.md (research links, E2B integration discussion)
- **Dependencies**: ADR-013 (new), ADR-011 (superseded), spec 005 (env variable change), spec 006 (logging service name change)

## Required Changes

### spec.md Changes

#### Change 1: FR-5 — Model selection
- **Location**: `spec.md`, line 17
- **Current**: `FR-5: Support model selection: GPT-4o-mini (default) or Gemma 4 via E2B sandbox. Model specified by user in query request.`
- **New**: `FR-5: Support model selection: GPT-4o-mini (default) or Gemma 4 2B via Ollama (localhost:11434). Model specified by user in query request.`
- **Rationale**: Replace E2B with Ollama as the alternative LLM provider.

#### Change 2: NFR-5 — Fallback behavior
- **Location**: `spec.md`, line 29
- **Current**: `NFR-5: If E2B is unavailable, fall back to GPT-4o-mini with a notification in the response.`
- **New**: `NFR-5: If Ollama is unavailable, fall back to GPT-4o-mini with a notification in the response.`
- **Rationale**: Fallback pattern is the same, but the service name changes.

#### Change 3: Failure case — E2B unavailable
- **Location**: `spec.md`, line 41
- **Current**: `**E2B unavailable**: Fall back to GPT-4o-mini. Include "model_fallback": "gpt-4o-mini" in response metadata.`
- **New**: `**Ollama unavailable**: Fall back to GPT-4o-mini. Include "model_fallback": "gpt-4o-mini" in response metadata.`
- **Rationale**: Service name change.

#### Change 4: Success criteria — E2B fallback
- **Location**: `spec.md`, line 55
- **Current**: `E2B fallback to GPT-4o-mini works transparently.`
- **New**: `Ollama fallback to GPT-4o-mini works transparently.`
- **Rationale**: Service name change.

### plan.md Changes

#### Change 5: LLM Synthesis Flow — Model selection
- **Location**: `plan.md`, lines 44-49
- **Current**:
  ```
  - `"gemma-4"`: E2B Sandbox API
  ...
  - Gemma 4: E2B sandbox execution with streaming output
  ```
- **New**:
  ```
  - `"gemma-4-2b"`: Ollama local API (localhost:11434)
  ...
  - Gemma 4 2B: Ollama `/v1/chat/completions` endpoint with streaming output
  ```
- **Rationale**: Replace E2B SDK integration with Ollama OpenAI-compatible API. Note the model identifier changes from `"gemma-4"` to `"gemma-4-2b"` to reflect the specific model size.

#### Change 6: Error handling table — E2B unavailable row
- **Location**: `plan.md`, line 172
- **Current**: `| E2B unavailable | Connection error | token: {"content": "[Using GPT-4o-mini as fallback] "} | Retry with GPT-4o-mini |`
- **New**: `| Ollama unavailable | Connection error (localhost:11434) | token: {"content": "[Using GPT-4o-mini as fallback] "} | Retry with GPT-4o-mini |`
- **Rationale**: Service name change. Detection mechanism is a connection error to localhost rather than to a cloud service.

#### Change 7: Related ADRs
- **Location**: `plan.md`, line 179
- **Current**: `- ADR-011: Use GPT-4o-mini as primary LLM`
- **New**: `- ADR-013: Switch from E2B to Ollama (Gemma 4 2B) for Local LLM (supersedes ADR-011)`
- **Rationale**: ADR-011 is superseded.

### tasks.md Changes

#### Change 8: Foundation task — E2B SDK
- **Location**: `tasks.md`, line 6
- **Current**: `- [ ] Set up E2B SDK client with async support (estimate: 1.5h)`
- **New**: `- [ ] Set up Ollama client using OpenAI-compatible API at localhost:11434 (estimate: 1h)`
- **Rationale**: Ollama uses OpenAI-compatible API, simplifying integration (reduced estimate from 1.5h to 1h).

#### Change 9: Core task — E2B streaming synthesis
- **Location**: `tasks.md`, line 15
- **Current**: `- [ ] Implement E2B Gemma 4 streaming synthesis: async generator yielding SSE events from E2B sandbox (estimate: 3h)`
- **New**: `- [ ] Implement Ollama Gemma 4 2B streaming synthesis: async generator yielding SSE events from Ollama /v1/chat/completions endpoint (estimate: 2h)`
- **Rationale**: Ollama's OpenAI-compatible API reduces implementation effort (reduced estimate from 3h to 2h).

#### Change 10: Core task — E2B fallback
- **Location**: `tasks.md`, line 17
- **Current**: `- [ ] Implement E2B fallback: detect E2B unavailability, switch to GPT-4o-mini, emit notification event (estimate: 1.5h)`
- **New**: `- [ ] Implement Ollama fallback: detect Ollama unavailability (connection refused at localhost:11434), switch to GPT-4o-mini, emit notification event (estimate: 1.5h)`
- **Rationale**: Detection mechanism changes to localhost connection check.

#### Change 11: Integration test — E2B fallback
- **Location**: `tasks.md`, line 33
- **Current**: `- [ ] Integration test: E2B fallback — simulate E2B failure, verify GPT-4o-mini fallback (estimate: 2h)`
- **New**: `- [ ] Integration test: Ollama fallback — simulate Ollama unavailability, verify GPT-4o-mini fallback (estimate: 2h)`
- **Rationale**: Test target changes.

#### Change 12: Documentation task — E2B integration
- **Location**: `tasks.md`, line 42
- **Current**: `- [ ] Document E2B integration setup and configuration (estimate: 1h)`
- **New**: `- [ ] Document Ollama setup: installation, model pull (gemma-4-2b), configuration, and health check (estimate: 1h)`
- **Rationale**: Documentation changes from cloud API setup to local service setup.

### notes.md Changes

#### Change 13: Research links — E2B SDK
- **Location**: `notes.md`, line 6
- **Current**: `- [E2B Code Interpreter SDK](https://e2b.dev/docs) — E2B sandbox API for running Gemma 4`
- **New**: `- [Ollama API Documentation](https://github.com/ollama/ollama/blob/main/docs/api.md) — Ollama REST API and OpenAI compatibility`
- **Rationale**: Replace E2B documentation link with Ollama documentation.

#### Change 14: E2B Integration Considerations section
- **Location**: `notes.md`, lines 51-59
- **Current**: Entire "E2B Integration Considerations" section discussing E2B cloud sandbox differences.
- **New**: Replace with "Ollama Integration Considerations" section:
  ```
  ### Ollama Integration Considerations
  Ollama runs Gemma 4 2B locally via localhost:11434. Key differences from OpenAI:
  - OpenAI-compatible API at `/v1/chat/completions` — can reuse same client code with different base URL
  - Streaming via chunked HTTP responses (same SSE-compatible format)
  - Higher latency than GPT-4o-mini for first token (~2-5s cold start, ~1s warm)
  - Less reliable instruction following (2B model has limited capability vs GPT-4o-mini)
  - Data stays local — true privacy, no external data transmission
  - Ollama must be installed and running separately from the RAG application
  - Model must be pre-pulled: `ollama pull gemma4:2b` (Gemma 4 2B)
  
  The Ollama integration should be abstracted behind the same `synthesize_answer()` interface
  so that model selection is transparent to the rest of the pipeline. Since Ollama supports
  the OpenAI-compatible API, the same `openai.AsyncOpenAI` client can be used with a different
  `base_url` parameter.
  ```
- **Rationale**: Complete replacement of E2B-specific integration notes with Ollama-specific notes.

## Validation Checklist
- [x] All E2B references replaced with Ollama in spec.md (4 locations)
- [x] All E2B references replaced with Ollama in plan.md (3 locations)
- [x] All E2B references replaced with Ollama in tasks.md (5 locations)
- [x] All E2B references replaced with Ollama in notes.md (2 locations)
- [x] Model identifier updated from "gemma-4" to "gemma-4-2b"
- [x] API contracts updated (E2B SDK → Ollama OpenAI-compatible API)
- [x] Data flows updated (cloud → local)
- [x] ADR reference updated (011 → 013)
- [x] No inconsistencies introduced

## Notes
- The model identifier in the query API changes from `"gemma-4"` to `"gemma-4-2b"` to accurately reflect the specific model variant. This is a breaking API change if any clients depend on `"gemma-4"` — acceptable since the system is not yet implemented.
- Task time estimates are reduced for some items because Ollama's OpenAI-compatible API is simpler to integrate than E2B's custom SDK.
- The `synthesize_answer()` interface signature changes: `model` parameter accepts `"gemma-4-2b"` instead of `"gemma-4"`.
