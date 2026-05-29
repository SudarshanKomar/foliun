# Review Report: 006-observability (E2B → Ollama Migration)

## Change Triggered By
- **ADR-013**: Switch from E2B to Ollama (Gemma 4 2B) for Local LLM
- Supersedes ADR-011

## Impact Assessment
- **Severity**: Low — logging wrapper and sensitive data filtering references change
- **Scope**: plan.md (external API call logging, sensitive data filtering), tasks.md (E2B logging task)
- **Dependencies**: ADR-013, spec 004 (model integration)

## Required Changes

### plan.md Changes

#### Change 1: External API Call Logging — Section title and description
- **Location**: `plan.md`, line 153-154
- **Current**: `Wrapper for all OpenAI and E2B API calls.`
- **New**: `Wrapper for all OpenAI and Ollama API calls.`
- **Rationale**: Service name change.

#### Change 2: External API Call Logging — Service parameter comment
- **Location**: `plan.md`, line 158
- **Current**: `service: str,  # "openai" or "e2b"`
- **New**: `service: str,  # "openai" or "ollama"`
- **Rationale**: Service identifier change in logging code.

#### Change 3: Sensitive Data Filtering — E2B_API_KEY
- **Location**: `plan.md`, line 189
- **Current**: `- \`API_KEY\`, \`OPENAI_API_KEY\`, \`E2B_API_KEY\` values`
- **New**: `- \`API_KEY\`, \`OPENAI_API_KEY\` values`
- **Rationale**: `E2B_API_KEY` no longer exists. `OLLAMA_BASE_URL` is not a secret (it's a localhost URL) and does not need sensitive data filtering. This simplifies the filtering rules.

### tasks.md Changes

#### Change 4: External API call logging task — E2B
- **Location**: `tasks.md`, line 17
- **Current**: `- [ ] Implement external API call logging wrapper for E2B calls (estimate: 1h)`
- **New**: `- [ ] Implement external API call logging wrapper for Ollama calls (estimate: 1h)`
- **Rationale**: Service name change.

### spec.md Changes

#### Change 5: FR-5 — External API call logging
- **Location**: `spec.md`, line 24
- **Current**: `FR-5: Log all external API calls (OpenAI, E2B) with request type, latency, status, and error details.`
- **New**: `FR-5: Log all external API calls (OpenAI, Ollama) with request type, latency, status, and error details.`
- **Rationale**: Service name change. Note: Ollama is technically a local service, not external, but logging it alongside OpenAI is still appropriate for observability.

### notes.md Changes
No direct E2B references in notes.md. No changes required.

## Validation Checklist
- [ ] E2B service name replaced with Ollama in logging wrapper (2 locations in plan.md)
- [ ] E2B_API_KEY removed from sensitive data filter list
- [ ] E2B logging task renamed to Ollama in tasks.md
- [ ] E2B replaced with Ollama in spec.md FR-5
- [ ] No inconsistencies introduced
- [ ] Consistent with spec 004 and spec 005 changes

## Notes
- The observability impact is minimal. The logging wrapper is service-agnostic — only the service name string changes from `"e2b"` to `"ollama"`.
- Ollama being local means latency logs for the Ollama service will show lower network latency (localhost) but potentially higher inference latency (local hardware vs cloud GPU). This is expected and documented.
- The removal of `E2B_API_KEY` from the sensitive data filter simplifies the filtering logic slightly — `OLLAMA_BASE_URL` is a non-secret URL.
