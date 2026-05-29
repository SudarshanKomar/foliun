# Review Report: 005-api-and-auth (E2B → Ollama Migration)

## Change Triggered By
- **ADR-013**: Switch from E2B to Ollama (Gemma 4 2B) for Local LLM
- Supersedes ADR-011

## Impact Assessment
- **Severity**: Medium — only affects environment variable configuration and query model enum
- **Scope**: plan.md (configuration section, query request schema)
- **Dependencies**: ADR-013, spec 004 (model selection)

## Required Changes

### plan.md Changes

#### Change 1: Environment Variables — E2B_API_KEY
- **Location**: `plan.md`, line 209
- **Current**: `E2B_API_KEY=e2b_...                    # Optional`
- **New**: `OLLAMA_BASE_URL=http://localhost:11434    # Optional, default shown`
- **Rationale**: E2B API key is replaced with Ollama base URL. Unlike E2B (which needed a secret API key), Ollama uses a plain URL (no secret). This also simplifies security — one fewer secret to manage.

#### Change 2: Query Request Schema — model enum
- **Location**: `plan.md`, query request Pydantic schema section
- **Current**:
  ```python
  class QueryRequest(BaseModel):
      query: str = Field(..., min_length=1, max_length=2000)
      model: Literal["gpt-4o-mini", "gemma-4"] = "gpt-4o-mini"
  ```
- **New**:
  ```python
  class QueryRequest(BaseModel):
      query: str = Field(..., min_length=1, max_length=2000)
      model: Literal["gpt-4o-mini", "gemma-4-2b"] = "gpt-4o-mini"
  ```
- **Rationale**: Model identifier changes from `"gemma-4"` to `"gemma-4-2b"` to reflect the specific Ollama model variant.

### spec.md Changes
No direct E2B references in spec.md. However:

#### Change 3: Health endpoint consideration
- **Location**: `spec.md`, health endpoint description (indirect)
- **Current**: Health check references PostgreSQL, Redis, OpenAI. E2B was not explicitly listed in the health check but was implied as a dependency.
- **New**: Health check should include Ollama connectivity check (GET `http://localhost:11434/api/tags`). This is a **new consideration** — unlike E2B (which was optional and cloud-based), Ollama running locally can be health-checked directly.
- **Rationale**: Local services are easier to health-check and should be included.

### notes.md Changes
No direct E2B references in notes.md.

## Validation Checklist
- [ ] E2B_API_KEY replaced with OLLAMA_BASE_URL in environment variables
- [ ] Model enum updated from "gemma-4" to "gemma-4-2b"
- [ ] Health check consideration documented for Ollama
- [ ] No inconsistencies introduced
- [ ] Consistent with spec 004 model identifier change

## Notes
- The security implications are simplified: `E2B_API_KEY` was a secret that needed to be protected in logs and environment. `OLLAMA_BASE_URL` is a non-secret URL (typically `http://localhost:11434`), reducing the sensitive data surface.
- The health endpoint (`GET /api/v1/health`) should be updated to include Ollama status when the Ollama model is configured. This is a minor enhancement, not a breaking change.
