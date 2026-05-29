# Consistency Verification Report

## Executive Summary

This report documents a comprehensive cross-verification of all AI Research Workspace RAG system documentation against the finalized system overview (`/docs/architecture/system-overview.md`) as the source of truth. The verification covered:

- **1 system overview** (source of truth)
- **13 ADRs** (001–013, including 1 superseded, 1 template)
- **24 spec files** (6 specs × 4 files each: spec, plan, tasks, notes)
- **4 spec templates**
- **4 migration review reports** (E2B → Ollama)
- **2 architecture review reports**

### Findings Summary

| Severity | Count | Description |
|----------|-------|-------------|
| **Critical** | 0 | No blocking inconsistencies found |
| **High** | 2 | Numeric target conflicts between documents |
| **Medium** | 7 | Stale references, missing info, scope mismatches |
| **Low** | 3 | Minor reference gaps, cosmetic issues |
| **Total** | **12** | |

### Overall Assessment

The documentation suite is **well-structured and largely consistent**. The E2B → Ollama migration was executed thoroughly across all active source files — no stale E2B references remain in any active document. The primary issues are: (1) two numeric target conflicts between the system overview and spec-level NFRs, (2) several stale ADR-011 references that should point to ADR-013, and (3) a potentially incorrect Ollama model pull command.

---

## Baseline: System Overview Key Facts

The following baseline was extracted from `/docs/architecture/system-overview.md` and used for all cross-verification.

### Technology Stack
| Component | Value |
|-----------|-------|
| Backend | FastAPI (Python 3.11+), Uvicorn |
| Database | PostgreSQL 16 + pgvector 0.7+ |
| Job Queue | Redis + arq |
| Embedding | OpenAI `text-embedding-3-small` (1536d) |
| Reranking | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Cloud LLM | GPT-4o-mini |
| Alternative LLM | Gemma 4 2B via Ollama (localhost:11434) — ADR-013 |
| Chunking | Recursive character, 512 tokens, 20% (102 token) overlap |
| Score Fusion | RRF (k=60) |
| Text Extraction | PyMuPDF (fitz) |
| Streaming | Server-Sent Events (SSE) |

### Key Numeric Values
| Parameter | Value |
|-----------|-------|
| Embedding dimensions | 1536 |
| HNSW m | 16 |
| HNSW ef_construction | 64 |
| HNSW ef_search | 40 |
| Chunk size | 512 tokens |
| Chunk overlap | 102 tokens (20%) |
| RRF k | 60 |
| Top-K per query | 20 |
| After RRF | Top 30 |
| After reranking | Top 10 |
| Relevance threshold | > 0.5 |
| Context budget | ~4000 tokens |
| File size limit | 50MB |
| Retries | 3× (1s, 4s, 16s backoff) |
| Query length | 1–2000 chars |
| SSE timeout | 120s |
| First token target | < 3s |
| Query latency target | < 5s (excl. streaming) |
| Ingestion target | < 30s for 10-page PDF |

### Model Identifiers
- `"gpt-4o-mini"` (default)
- `"gemma-4-2b"` (alternative)

### API Endpoints
| Method | Endpoint | Auth |
|--------|----------|------|
| POST | `/api/v1/documents` | API Key |
| GET | `/api/v1/documents` | API Key |
| GET | `/api/v1/documents/{id}/status` | API Key |
| POST | `/api/v1/query` | API Key |
| GET | `/api/v1/health` | None |

### Environment Variables (from spec 005)
`API_KEY`, `DATABASE_URL`, `REDIS_URL`, `OPENAI_API_KEY`, `OLLAMA_BASE_URL`, `CORS_ORIGINS`, `STORAGE_PATH`, `LOG_LEVEL`

---

## Detailed Issues

### HIGH-001: First-Token Latency Target Conflicts with Retrieval Latency Target

- **Severity**: High
- **Documents**: `system-overview.md` (lines 396–397) vs `specs/003-retrieval-pipeline/spec.md` (NFR-1, line 26)
- **Description**: The system overview defines two performance targets:
  - *Query latency*: < 5 seconds end-to-end (excluding LLM streaming)
  - *First token time*: < 3 seconds from query submission to first streamed token

  However, spec 003 defines retrieval latency (rewrite + embed + search + RRF + rerank) as < 4 seconds. If retrieval alone can take up to 4 seconds, plus context construction (~100ms) plus LLM first-token latency (~500ms for GPT-4o-mini), the first streamed token cannot arrive within 3 seconds.

- **Impact**: A query hitting the spec 003 upper bound (3.5–4s retrieval) would violate the system overview's 3-second first-token target.
- **Recommendation**: Either tighten spec 003's retrieval target to < 2.5s, or relax the system overview's first-token target to < 5s (matching the overall query latency target). Alternatively, clarify that these are targets for *typical* queries, not worst-case guarantees.

---

### HIGH-002: Cross-Encoder Reranking Latency — Target vs Estimated Performance

- **Severity**: High
- **Documents**: `system-overview.md` (line 399), `specs/003-retrieval-pipeline/spec.md` (NFR-4, line 29), `adrs/006-use-cross-encoder-reranking.md` (line 27), `specs/003-retrieval-pipeline/notes.md` (lines 31–32)
- **Description**: The system overview and spec 003 both require cross-encoder reranking of 30 candidates to complete in **< 500ms on CPU**. However:
  - ADR-006 states: "~50ms per (query, chunk) pair, ~1.5s for 30 candidates"
  - Spec 003 notes state: "~50ms per (query, chunk) pair → ~1.5s for 30 pairs (sequential)"

  The 500ms target is **3× faster** than the estimated 1.5s sequential performance documented in both the ADR and notes.

- **Impact**: The reranking stage will routinely exceed its 500ms target, which cascades into the overall retrieval latency exceeding 4s, which further exacerbates HIGH-001.
- **Recommendation**: Either (a) revise the reranking target to < 1.5s and adjust upstream latency budgets accordingly, or (b) document a parallelization or batching strategy that achieves 500ms (e.g., `sentence-transformers` batch inference), and update ADR-006 and spec 003 notes to reflect this.

---

### MED-001: Stale ADR-011 Reference in ADR-008

- **Severity**: Medium
- **Document**: `adrs/008-use-sse-streaming.md` (line 42)
- **Description**: Related ADRs section references `ADR-011: Use GPT-4o-mini as primary LLM`. ADR-011 has been superseded by ADR-013.
- **Recommendation**: Update to: `ADR-013: Switch from E2B to Ollama (Gemma 4 2B) for Local LLM (supersedes ADR-011)`

---

### MED-002: Stale ADR-011 Reference in ADR-012

- **Severity**: Medium
- **Document**: `adrs/012-remove-general-knowledge-fallback.md` (line 40)
- **Description**: Related ADRs section references `ADR-011: Use GPT-4o-mini as primary LLM`. ADR-011 has been superseded by ADR-013.
- **Recommendation**: Update to: `ADR-013: Switch from E2B to Ollama (Gemma 4 2B) for Local LLM (supersedes ADR-011)`

---

### MED-003: Stale ADR-011 Reference in Spec 003 Plan

- **Severity**: Medium
- **Document**: `specs/003-retrieval-pipeline/plan.md` (line 162)
- **Description**: Related ADRs section references `ADR-011: Use GPT-4o-mini as primary LLM`. ADR-011 has been superseded by ADR-013.
- **Recommendation**: Update to: `ADR-013: Switch from E2B to Ollama (Gemma 4 2B) for Local LLM (supersedes ADR-011)`

---

### MED-004: Incorrect Ollama Model Pull Command in Spec 004 Notes

- **Severity**: Medium
- **Document**: `specs/004-context-and-synthesis/notes.md` (line 59)
- **Description**: The Ollama integration section states:
  ```
  Model must be pre-pulled: `ollama pull gemma3:4b` (or appropriate Gemma 4 2B tag)
  ```
  This references `gemma3:4b` (Gemma 3, 4B variant), which is a **different model** than "Gemma 4 2B" used throughout the project. The parenthetical "(or appropriate Gemma 4 2B tag)" acknowledges uncertainty but the primary command is misleading.

  Meanwhile, `specs/004-context-and-synthesis/tasks.md` (line 42) references `gemma-4-2b` as the model tag, creating a conflict within the same spec directory.
- **Recommendation**: Determine the correct Ollama model tag for Gemma 4 2B and update both locations consistently. If the exact tag is not yet confirmed, use a placeholder with a clear TODO marker.

---

### MED-005: Health Endpoint Missing Ollama Dependency Check

- **Severity**: Medium
- **Documents**: `specs/005-api-and-auth/spec.md` (FR-5, line 17), `specs/005-api-and-auth/plan.md` (lines 155–184)
- **Description**: The health endpoint specification lists PostgreSQL, Redis, and OpenAI as dependency checks, but does **not** include Ollama. Since Ollama is now a system dependency (per ADR-013), it should be checked when configured. The spec 005 migration review report (`review-report-e2b-to-ollama.md`, Change 3) identified this as a needed enhancement but the spec was not updated.
- **Recommendation**: Add Ollama connectivity check (`GET http://localhost:11434/api/tags`) to the health endpoint spec and plan. Mark it as optional (only checked when `OLLAMA_BASE_URL` is configured).

---

### MED-006: Ingestion Time Target Scope Mismatch

- **Severity**: Medium
- **Documents**: `system-overview.md` (line 398) vs `specs/001-document-ingestion/spec.md` (NFR-1, line 24)
- **Description**:
  - System overview: "Ingestion time: < 30 seconds for a 10-page PDF **(extraction + chunking + embedding)**"
  - Spec 001 NFR-1: "Ingestion time must be < 30 seconds for a 10-page PDF **(extraction + chunking, excluding embedding)**"

  The system overview includes embedding in the 30s target; spec 001 explicitly excludes it. While both targets are achievable (spec 001 stages take ~4s, spec 002 embedding takes < 10s, total ~14s), the scope definition differs.
- **Recommendation**: Align the scope. Either update spec 001 to include embedding in its target (since ADR-009 establishes a single worker pipeline), or add a clarifying note to the system overview specifying the combined target covers specs 001 + 002.

---

### MED-007: Migration Review Report Validation Checklists Unchecked

- **Severity**: Medium
- **Documents**: All 4 migration review reports:
  - `adrs/review-report-e2b-to-ollama.md`
  - `specs/004-context-and-synthesis/review-report-e2b-to-ollama.md`
  - `specs/005-api-and-auth/review-report-e2b-to-ollama.md`
  - `specs/006-observability/review-report-e2b-to-ollama.md`
- **Description**: All validation checklists in the review reports contain unchecked boxes (`- [ ]`), despite all described changes having been applied to the source files. This gives a false impression that the migration is incomplete.
- **Recommendation**: Mark all validation checklist items as checked (`- [x]`) to accurately reflect completion status.

---

### LOW-001: Spec 005 Plan Missing ADR-013 in Related ADRs

- **Severity**: Low
- **Document**: `specs/005-api-and-auth/plan.md` (lines 268–271)
- **Description**: Related ADRs lists ADR-002, ADR-008, and ADR-010, but does not reference ADR-013 despite the plan including `OLLAMA_BASE_URL` environment variable and `"gemma-4-2b"` model enum — both direct consequences of ADR-013.
- **Recommendation**: Add `ADR-013: Switch from E2B to Ollama (Gemma 4 2B) for Local LLM` to the Related ADRs section.

---

### LOW-002: Spec 006 Plan Missing ADR-013 in Related ADRs

- **Severity**: Low
- **Document**: `specs/006-observability/plan.md` (lines 194–196)
- **Description**: Related ADRs lists ADR-002 and ADR-009, but does not reference ADR-013 despite the plan discussing Ollama API call logging and having been updated as part of the E2B → Ollama migration.
- **Recommendation**: Add `ADR-013: Switch from E2B to Ollama (Gemma 4 2B) for Local LLM` to the Related ADRs section.

---

### LOW-003: Conflicting Model Tags Between Spec 004 Notes and Tasks

- **Severity**: Low
- **Document**: `specs/004-context-and-synthesis/notes.md` (line 59) vs `specs/004-context-and-synthesis/tasks.md` (line 42)
- **Description**: `notes.md` uses `gemma3:4b` as the Ollama pull tag, while `tasks.md` uses `gemma-4-2b`. These are inconsistent with each other. (Related to MED-004.)
- **Recommendation**: Resolve when the correct Ollama tag is determined (see MED-004).

---

## Document-Specific Findings

### System Overview (`/docs/architecture/system-overview.md`)
- **Status**: ✅ Clean — serves as source of truth
- **E2B references**: None (all migrated to Ollama)
- **Internal consistency**: All sections align (C4 diagrams, data flows, state machines, technology table, domain language, NFRs)
- **Issues**: Source of HIGH-001, HIGH-002 (target values defined here conflict with downstream specs), and one side of MED-006

### ADRs

| ADR | Status | Issues |
|-----|--------|--------|
| ADR-001 (pgvector) | ✅ Clean | No issues |
| ADR-002 (FastAPI) | ✅ Clean | No issues |
| ADR-003 (Redis/arq) | ✅ Clean | No issues |
| ADR-004 (Embeddings) | ✅ Clean | No issues |
| ADR-005 (RRF) | ✅ Clean | No issues |
| ADR-006 (Cross-encoder) | ⚠️ | Source of HIGH-002 (1.5s estimate vs 500ms target) |
| ADR-007 (Chunking) | ✅ Clean | No issues |
| ADR-008 (SSE) | ⚠️ | MED-001: Stale ADR-011 reference |
| ADR-009 (Single worker) | ✅ Clean | No issues |
| ADR-010 (API key auth) | ✅ Clean | E2B → Ollama migration applied |
| ADR-011 (LLM selection) | ✅ Historical | Correctly marked as superseded by ADR-013 |
| ADR-012 (No gen. knowledge) | ⚠️ | MED-002: Stale ADR-011 reference |
| ADR-013 (E2B → Ollama) | ✅ Clean | No issues |

### Specs

| Spec | spec.md | plan.md | tasks.md | notes.md |
|------|---------|---------|----------|----------|
| 001 (Ingestion) | ⚠️ MED-006 | ✅ Clean | ✅ Clean | ✅ Clean |
| 002 (Embedding) | ✅ Clean | ✅ Clean | ✅ Clean | ✅ Clean |
| 003 (Retrieval) | ⚠️ HIGH-001, HIGH-002 | ⚠️ MED-003 | ✅ Clean | ⚠️ HIGH-002 |
| 004 (Context/Synthesis) | ✅ Clean | ✅ Clean | ✅ Clean | ⚠️ MED-004, LOW-003 |
| 005 (API/Auth) | ⚠️ MED-005 | ⚠️ MED-005, LOW-001 | ✅ Clean | ✅ Clean |
| 006 (Observability) | ✅ Clean | ⚠️ LOW-002 | ✅ Clean | ✅ Clean |

### Templates
- **ADR template** (`/adrs/templates/adr.md`): ✅ Clean — properly structured with all required sections
- **Spec templates** (`/specs/templates/`): ✅ Clean — all 4 templates (spec, plan, tasks, notes) are properly structured and all actual specs follow the template format

### Migration Review Reports
- All 4 reports: ⚠️ MED-007 (unchecked validation checklists)
- Content accuracy: ✅ All described changes have been correctly applied

---

## Consistency Matrix

### Technology Naming Consistency

| Term | System Overview | ADRs | Specs | Status |
|------|----------------|------|-------|--------|
| PostgreSQL 16 + pgvector 0.7+ | ✅ | ✅ ADR-001 | ✅ All | Consistent |
| FastAPI (Python 3.11+) | ✅ | ✅ ADR-002 | ✅ All | Consistent |
| Redis + arq | ✅ | ✅ ADR-003 | ✅ All | Consistent |
| text-embedding-3-small (1536d) | ✅ | ✅ ADR-004 | ✅ All | Consistent |
| ms-marco-MiniLM-L-6-v2 | ✅ | ✅ ADR-006 | ✅ All | Consistent |
| GPT-4o-mini | ✅ | ✅ ADR-013 | ✅ All | Consistent |
| Gemma 4 2B via Ollama | ✅ | ✅ ADR-013 | ✅ All | Consistent |
| `"gemma-4-2b"` identifier | ✅ | ✅ ADR-013 | ✅ All | Consistent |
| PyMuPDF (fitz) | ✅ | — | ✅ 001 | Consistent |
| tiktoken (cl100k_base) | ✅ | — | ✅ 001, 004 | Consistent |
| Ollama model pull tag | N/A | N/A | ⚠️ Conflicting | **Inconsistent** (MED-004) |

### Numeric Value Consistency

| Parameter | System Overview | Specs | ADRs | Status |
|-----------|----------------|-------|------|--------|
| Chunk size (512 tokens) | ✅ | ✅ 001, 003, 004 | ✅ 007 | Consistent |
| Overlap (102 tokens, 20%) | ✅ | ✅ 001 | ✅ 007 | Consistent |
| Embedding dims (1536) | ✅ | ✅ 001, 002, 003 | ✅ 001, 004 | Consistent |
| HNSW m=16, ef_c=64 | ✅ | ✅ 002 | ✅ 001 | Consistent |
| HNSW ef_search=40 | ✅ | ✅ 002, 003 | — | Consistent |
| RRF k=60 | ✅ | ✅ 003 | ✅ 005 | Consistent |
| Top-20/30/10 funnel | ✅ | ✅ 003 | ✅ 005, 006 | Consistent |
| Threshold > 0.5 | ✅ | ✅ 003, 004 | ✅ 006, 012 | Consistent |
| Context ~4000 tokens | ✅ | ✅ 004 | — | Consistent |
| File size ≤ 50MB | ✅ | ✅ 001, 005 | — | Consistent |
| Retry 3× (1s, 4s, 16s) | ✅ | ✅ 001, 002 | ✅ 003 | Consistent |
| Query 1–2000 chars | ✅ | ✅ 003, 005 | — | Consistent |
| SSE timeout 120s | ✅ | ✅ 004 | ✅ 008 | Consistent |
| First token < 3s | ✅ | ⚠️ 003, 004 | — | **Conflict** (HIGH-001) |
| Rerank < 500ms | ✅ | ⚠️ 003 notes | ⚠️ 006 | **Conflict** (HIGH-002) |
| Ingestion < 30s scope | ✅ (incl. embed) | ⚠️ 001 (excl. embed) | — | **Mismatch** (MED-006) |

### API Naming Consistency
All 5 endpoints are consistently named across system overview, spec 001 plan, and spec 005 plan. ✅

### Environment Variable Consistency
All environment variables are consistently named across spec 005 plan and ADR-013. `OLLAMA_BASE_URL` replaces `E2B_API_KEY` everywhere. ✅

### ADR Reference Consistency

| Document | References | Status |
|----------|-----------|--------|
| ADR-008 | ADR-011 | ⚠️ Should be ADR-013 |
| ADR-012 | ADR-011 | ⚠️ Should be ADR-013 |
| Spec 003 plan | ADR-011 | ⚠️ Should be ADR-013 |
| Spec 004 plan | ADR-013 | ✅ Updated |
| Spec 005 plan | Missing ADR-013 | ⚠️ Should include |
| Spec 006 plan | Missing ADR-013 | ⚠️ Should include |

### E2B Reference Verification
**No stale E2B references** exist in any active source document. All remaining E2B mentions are in:
- `adrs/011-llm-model-selection.md` — correctly marked as superseded (historical)
- `adrs/013-switch-from-e2b-to-ollama.md` — migration context (expected)
- All `review-report-e2b-to-ollama.md` files — migration documentation (expected)
- `docs/architecture/review-report-e2b-to-ollama.md` — historical review (expected)

✅ **Migration complete** — no cleanup needed.

### Phase 1 vs Phase 2+ Scope Verification
All specs correctly scope their requirements to Phase 1. No Phase 2+ features (hybrid search, semantic chunking, RBAC, Prometheus, OCR) are included in any Phase 1 spec. ✅

---

## Recommendations

### Immediate Actions (Before Implementation)

1. **Resolve latency budget conflict (HIGH-001, HIGH-002)**
   - Option A: Revise system overview targets to: first token < 5s, reranking < 1.5s
   - Option B: Revise spec 003 retrieval target to < 2.5s and document batched cross-encoder inference achieving < 500ms
   - *Recommendation*: Option A is more realistic given documented model performance

2. **Update stale ADR-011 references (MED-001, MED-002, MED-003)**
   - Update 3 files to reference ADR-013 instead of ADR-011
   - Simple find-and-replace, low risk

3. **Resolve Ollama model tag (MED-004, LOW-003)**
   - Verify the correct Ollama registry tag for Gemma 4 2B
   - Update `specs/004-context-and-synthesis/notes.md` line 59
   - Update `specs/004-context-and-synthesis/tasks.md` line 42

### Short-Term Actions (During Implementation)

4. **Add Ollama to health endpoint (MED-005)**
   - Update spec 005 to include optional Ollama health check
   - Add to health response example

5. **Align ingestion time target scope (MED-006)**
   - Clarify in system overview or spec 001 whether the 30s target includes embedding

6. **Complete migration review checklists (MED-007)**
   - Mark all validation items as checked in the 4 review reports

7. **Add ADR-013 to Related ADRs (LOW-001, LOW-002)**
   - Update spec 005 plan and spec 006 plan

---

## Verification Methodology

1. **File-by-file reading**: Every `.md` file in `/docs/`, `/adrs/`, `/specs/`, and templates was read in full.
2. **Baseline extraction**: Key facts extracted from system overview into structured tables.
3. **Cross-verification**: Each ADR and spec checked against baseline for technology names, numeric values, API names, environment variables, model identifiers, and ADR references.
4. **E2B sweep**: Full-text grep for "E2B" across entire project to verify migration completeness.
5. **Consistency matrix**: Systematic comparison of all recurring values across all documents.

---

*Report generated: Comprehensive project-wide consistency verification*
*Source of truth: `/docs/architecture/system-overview.md`*
*Scope: All ADRs (001–013), all specs (001–006), all templates, all review reports*
