# Review Report: System Overview (E2B → Ollama Migration)

## Change Triggered By
- **ADR-013**: Switch from E2B to Ollama (Gemma 4 2B) for Local LLM
- Supersedes ADR-011

## Impact Assessment
- **Severity**: High
- **Scope**: System Context diagram, Container View diagram, External Entities, Technology Decisions table, Query State Machine, Key Assumptions, Evolution Path
- **Dependencies**: All specs referencing E2B (004, 005, 006), ADR-011, review-report.md

## Required Changes

### Change 1: System Context Diagram (C4 Level 1) — Lines 48-66
- **Location**: `## System Context (C4 Level 1)` — Mermaid diagram
- **Current**:
  ```
  API --> E2B[E2B Sandbox API]
  ...
  subgraph "External Services"
      OpenAI
      E2B
  end
  ```
- **New**:
  ```
  API --> Ollama[Ollama Local LLM]
  ...
  subgraph "Local Services"
      Ollama
  end
  ```
- **Rationale**: E2B was an external cloud service. Ollama runs locally and should not be in the "External Services" subgraph. It belongs in a new "Local Services" subgraph (or within the "AI Workspace System" boundary since it runs on the same infrastructure).

### Change 2: External Entities Description — Lines 68-73
- **Location**: `**External Entities:**` section
- **Current**:
  ```
  - **E2B Sandbox API**: Cloud-hosted sandbox running Gemma 4 as an alternative LLM for cost control
    (note: data is sent to E2B infrastructure — this is **not** local or private execution)
  ```
- **New**:
  ```
  - **Ollama**: Locally-hosted LLM server running Gemma 4 2B as an alternative LLM for privacy and
    cost control. Runs on localhost:11434. Data never leaves the user's infrastructure.
  ```
- **Rationale**: Ollama is a local service, not an external entity. The description should reflect its local nature and privacy benefits.

### Change 3: Assumption about E2B/Ollama — Line 73
- **Location**: `> **Assumption**: E2B is treated as a cost-control alternative...`
- **Current**:
  ```
  > **Assumption**: E2B is treated as a cost-control alternative, not a privacy-preserving option.
    For true local/private execution, a self-hosted model (e.g., Ollama) would be required and is
    deferred to Phase 2.
  ```
- **New**:
  ```
  > **Note**: Ollama provides true local/private execution. When using Ollama with Gemma 4 2B,
    no data leaves the user's infrastructure. This fulfills the privacy requirement that E2B could
    not satisfy. See ADR-013.
  ```
- **Rationale**: The assumption about deferring local LLM to Phase 2 is no longer valid — Ollama is now included in Phase 1.

### Change 4: Container View Diagram (C4 Level 2) — Lines 75-110
- **Location**: `## Container View (C4 Level 2)` — Mermaid diagram
- **Current**:
  ```
  subgraph "External Services"
      OpenAI[OpenAI API]
      E2B[E2B Sandbox API]
  end
  ...
  FastAPI --> E2B
  ```
- **New**:
  ```
  subgraph "External Services"
      OpenAI[OpenAI API]
  end
  subgraph "Local Services"
      Ollama[Ollama - Gemma 4 2B]
  end
  ...
  FastAPI --> Ollama
  ```
- **Rationale**: Ollama runs locally, separate from external cloud services. The container diagram should reflect this architectural distinction.

### Change 5: Technology Decisions Table — Line 356
- **Location**: `## Technology Decisions` table, row "Alternative LLM"
- **Current**:
  ```
  | Alternative LLM | Gemma 4 via E2B sandbox | Cost control alternative (not privacy — data sent to E2B) |
  ```
- **New**:
  ```
  | Alternative LLM | Gemma 4 2B via Ollama (localhost:11434) | True local/private execution, zero API cost, runs on low-end machines |
  ```
- **Rationale**: Reflects the new technology choice with accurate rationale.

### Change 6: Query State Machine — Line 301
- **Location**: `### Query/Retrieval Flow` — LLMSynthesis state description
- **Current**:
  ```
  - **LLMSynthesis**: Generate answer using selected LLM (GPT-4o-mini or Gemma 4 via E2B) with
    structured citation format
  ```
- **New**:
  ```
  - **LLMSynthesis**: Generate answer using selected LLM (GPT-4o-mini or Gemma 4 2B via Ollama)
    with structured citation format
  ```
- **Rationale**: Update LLM option description to reflect Ollama instead of E2B.

### Change 7: Key Assumptions — Line 459-460
- **Location**: `## Key Assumptions`, item 6
- **Current**:
  ```
  6. **E2B availability** — the E2B sandbox service must be reachable for the alternative LLM option
  ```
- **New**:
  ```
  6. **Ollama availability** — the Ollama service must be running locally (localhost:11434) for the
     alternative LLM option. Ollama does not require internet connectivity.
  ```
- **Rationale**: Availability assumption changes from cloud service to local service.

### Change 8: Evolution Path — Line 435
- **Location**: `## Evolution Path (Beyond Phase 1)` → Phase 2 list
- **Current**:
  ```
  - Self-hosted local LLM option (Ollama) for true privacy
  ```
- **New**: **Remove this line entirely.**
- **Rationale**: Ollama is now included in Phase 1. This is no longer a Phase 2 item.

## Validation Checklist
- [ ] All E2B references replaced with Ollama
- [ ] External entities updated (E2B → Ollama)
- [ ] Technology decisions updated
- [ ] Assumptions updated
- [ ] C4 diagrams updated (System Context, Container View)
- [ ] Query state machine updated
- [ ] Evolution path updated (remove Ollama from Phase 2)
- [ ] No inconsistencies introduced
- [ ] ADR-013 referenced where appropriate

## Notes
- The review-report.md (original architecture review) contains E2B references in its historical findings (C1 issue, technology assessment, testing strategy, risk table, improvement log). These are **historical records** and should NOT be modified — they document the original review findings accurately. The review report captures what was found at the time of review. ADR-013 and this migration review report document the subsequent decision to change.
- The system overview's Phase 1 Scope section (lines 15-44) does not mention E2B explicitly and does not need changes.
- Database schema is not affected — E2B was never referenced in schema definitions.
