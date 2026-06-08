# Consistency Verification Report

> **Historical note**: The baseline data in this report (sections below) was generated before the ADR-014 embedding model migration and ADR-013 LLM default changes. Values such as `text-embedding-3-small (1536d)` and `GPT-4o-mini (default)` in the baseline reflect the system state at that time. See the Intensive Review section (below) and the resolution report for the current architecture.

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
| Backend | FastAPI (Python 3.14), Uvicorn |
| Database | PostgreSQL 18 + pgvector 0.8.1 |
| Job Queue | Redis + arq |
| Embedding | OpenAI `text-embedding-3-small` (1536d) |
| Reranking | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Cloud LLM | GPT-4o-mini |
| Alternative LLM | Gemma 4 2B via Ollama (localhost:11434) — ADR-013 |
| Chunking | Recursive character, 512 tokens, 20% (102 token) overlap |
| Score Fusion | RRF (k=60) |
| Text Extraction | pypdf |
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
| PostgreSQL 18 + pgvector 0.8.1 | ✅ | ✅ ADR-001 | ✅ All | Consistent |
| FastAPI (Python 3.14) | ✅ | ✅ ADR-002 | ✅ All | Consistent |
| Redis + arq | ✅ | ✅ ADR-003 | ✅ All | Consistent |
| text-embedding-3-small (1536d) | ✅ | ✅ ADR-004 | ✅ All | Consistent |
| ms-marco-MiniLM-L-6-v2 | ✅ | ✅ ADR-006 | ✅ All | Consistent |
| GPT-4o-mini | ✅ | ✅ ADR-013 | ✅ All | Consistent |
| Gemma 4 2B via Ollama | ✅ | ✅ ADR-013 | ✅ All | Consistent |
| `"gemma-4-2b"` identifier | ✅ | ✅ ADR-013 | ✅ All | Consistent |
| pypdf | ✅ | — | ✅ 001 | Consistent |
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

---

# Intensive Project Review - Implementation Risk Assessment

## Executive Summary
- **Total findings**: 25
- **Critical issues**: 3
- **High priority issues**: 6
- **Medium priority issues**: 10
- **Low priority issues**: 6
- **Overall assessment**: **NEEDS ATTENTION** — 3 critical issues must be resolved before implementation

This intensive review was conducted after the E2B → Ollama (ADR-013) and OpenAI → local embedding (ADR-014) migrations, and after resolution of all 12 issues identified in the previous consistency verification report. The review read every file in the project (14 ADRs, 24 spec files, 4 templates, 1 ADR template, 6 review/migration reports, 1 system overview, 1 README) and focused on architectural contradictions, implementation risks, untouched areas, and subtle inconsistencies not caught by prior reviews.

---

## Critical Issues

### Issue 1: OpenAI Embedding Fallback Broken by Database Schema

- **Location**: `specs/001-document-ingestion/plan.md` line 190, `specs/002-embedding-and-storage/spec.md` lines 32-33, `docs/architecture/system-overview.md` line 193
- **Description**: The `chunks` table schema hardcodes `embedding VECTOR(768)`. pgvector enforces dimensionality at the column type level — a 1536-dimensional vector **cannot be inserted** into a `VECTOR(768)` column. Yet multiple documents describe an "optional fallback to OpenAI `text-embedding-3-small` (1536d)" as if it were a simple configuration switch via `EMBEDDING_MODEL=openai`:
  - Spec 002 spec.md FR-10: "Support optional fallback to OpenAI... (1536d)"
  - Spec 005 plan.md line 213: `EMBEDDING_MODEL=local` or `openai`
  - ADR-014: "Optional fallback: OpenAI `text-embedding-3-small` (1536d)"
  - System overview technology table line 359: "OpenAI... available as optional fallback"
  
  Switching to OpenAI requires: (1) ALTER TABLE to VECTOR(1536), (2) DROP and recreate the HNSW index, (3) re-embed all existing chunks. None of this is documented as a migration process.
- **Impact**: An implementer following the specs would create the schema with VECTOR(768) then attempt to insert 1536d vectors when `EMBEDDING_MODEL=openai`, resulting in a database error. The "optional fallback" is misleading — it is a full migration, not a config toggle.
- **Recommendation**: Either (a) remove the OpenAI fallback from Phase 1 scope entirely and defer to Phase 2 with a documented migration process, or (b) document the exact migration steps (schema change, index rebuild, re-embedding) required to switch models, and clarify in all specs that `EMBEDDING_MODEL` is a deployment-time decision, not a runtime toggle.

---

### Issue 2: Privacy Violation — Query Rewriting Always Calls OpenAI API

- **Location**: `specs/003-retrieval-pipeline/spec.md` FR-2 (line 14), `specs/003-retrieval-pipeline/plan.md` lines 20-28, `docs/architecture/system-overview.md` lines 265, 298, 335
- **Description**: Query rewriting is hardcoded to use GPT-4o-mini in all documents. The user's model selection (spec 005 `QueryRequest.model` field) only controls the answer synthesis LLM (spec 004), not query rewriting. This means:
  - A user who selects `"gemma-4-2b"` for privacy (per ADR-013: "Data never leaves the user's infrastructure") still has their **raw queries sent to OpenAI** during the rewriting stage.
  - This directly contradicts ADR-013's privacy promise and ADR-014's "local-first" architecture.
  - The system overview line 460 states "Internet connectivity optional" when using local models, but query rewriting requires internet (OpenAI API).
- **Impact**: Users who choose the local model for privacy are unknowingly exposing their queries to an external service. This is a fundamental architectural contradiction between the privacy goals (ADR-013, ADR-014) and the retrieval pipeline design (spec 003).
- **Recommendation**: Add a local query rewriting path when `model=gemma-4-2b`: either (a) use Ollama/Gemma 4 2B for rewriting with an appropriate prompt, (b) skip query rewriting entirely and use the original query only (graceful degradation already exists for this), or (c) document this as a known privacy limitation in ADR-013 and spec 003. Option (b) is simplest and aligns with the existing graceful degradation pattern.

---

### Issue 3: Tokenizer Mismatch Between Chunking and Embedding Model

- **Location**: `adrs/007-chunking-strategy.md` line 17, `specs/001-document-ingestion/spec.md` FR-5 (line 15), `specs/001-document-ingestion/plan.md` line 40, `adrs/014-migrate-to-local-embedding-model.md` line 23
- **Description**: Chunking uses `tiktoken` with `cl100k_base` encoding to measure chunk size at 512 tokens. This tokenizer is designed for OpenAI GPT models (BPE-based). However, the embedding model `BAAI/bge-base-en-v1.5` uses a BERT-based WordPiece tokenizer with a different vocabulary. A text that is 512 tokens in `cl100k_base` may be significantly **more** than 512 tokens in the bge tokenizer (WordPiece typically produces more tokens than BPE for the same text). ADR-014 states the model's max sequence length is 512 tokens — measured in its own tokenizer.
  
  ADR-007 line 17 explicitly states the tokenizer choice: `tiktoken with cl100k_base encoding (matches OpenAI models)`. This rationale is now stale after the embedding model migration.
  
  `sentence-transformers` silently truncates inputs that exceed the model's max sequence length. Chunks that are 512 `cl100k_base` tokens but >512 WordPiece tokens will be truncated during embedding, causing **silent information loss** at the end of affected chunks.
- **Impact**: A percentage of chunks (especially those with many short words, numbers, or technical terms — common in research papers) will be silently truncated during embedding. The truncated portion's semantic content is lost from the vector representation, degrading retrieval quality without any error or warning.
- **Recommendation**: Either (a) reduce the target chunk size to ~400 `cl100k_base` tokens to provide safety margin, (b) switch to the bge model's native tokenizer for chunk sizing, (c) add a validation step that checks chunk length against the bge tokenizer and logs warnings for chunks that would be truncated, or (d) document this as an accepted limitation with analysis of the expected truncation rate. Option (c) is recommended as a low-effort safety net.

---

## High Priority Issues

### Issue 1: System Overview Contradicts ADR-009 on Retry Behavior

- **Location**: `docs/architecture/system-overview.md` line 258 vs `adrs/009-single-worker-process.md` lines 23, 29
- **Description**: The system overview states: "Partial progress is tracked: if embedding fails, text extraction is not repeated." ADR-009 states the exact opposite: "Simplified error handling: if any stage fails, the entire job retries from the beginning" and "If embedding generation fails, text extraction and chunking are repeated on retry (wasted work)." These are directly contradictory statements about a core architectural behavior.
- **Impact**: An implementer would receive conflicting instructions about retry behavior. The single-worker design (ADR-009) inherently retries from the beginning, making the system overview's claim incorrect.
- **Recommendation**: Update `system-overview.md` line 258 to align with ADR-009: "If any pipeline stage fails, the entire job retries from the beginning (extraction through embedding). Partial progress tracking is at the document status level only."

---

### Issue 2: No Local Query Rewriting Path

- **Location**: `specs/003-retrieval-pipeline/spec.md` FR-2, `specs/003-retrieval-pipeline/plan.md` lines 20-28
- **Description**: Beyond the privacy concern (Critical Issue 2), there is no documented mechanism for performing query rewriting using the local LLM. The graceful degradation (NFR-7) only covers **failure** of GPT-4o-mini, not intentional avoidance. If the user runs the system offline (internet not available, per key assumption #2), query rewriting fails silently and degrades to single-query search every time.
- **Impact**: Offline users permanently lose the multi-query retrieval benefit (4 queries → 1 query), significantly reducing retrieval quality. This should be a documented, intentional design choice — not an implicit failure mode.
- **Recommendation**: Add explicit documentation: when running offline or with `model=gemma-4-2b`, the system either (a) uses Ollama for query rewriting with a simpler prompt, or (b) intentionally operates in single-query mode with a log entry explaining why.

---

### Issue 3: Memory Pressure on Minimum Stated Hardware

- **Location**: `adrs/013-switch-from-e2b-to-ollama.md` line 35, `adrs/014-migrate-to-local-embedding-model.md` lines 22-23, 73, `specs/002-embedding-and-storage/notes.md` lines 41-42
- **Description**: ADR-013 states Gemma 4 2B "requires ~4GB RAM" and "runs on low-end machines (4GB+ RAM)." The actual memory budget:
  - Embedding model (bge-base-en-v1.5): ~440MB
  - Cross-encoder reranker: ~200MB
  - Gemma 4 2B via Ollama: ~4GB (model loaded into memory by Ollama process)
  - PostgreSQL: ~256MB+ (shared_buffers default)
  - Redis: ~50MB+
  - Python/FastAPI runtime: ~100MB+
  - OS overhead: ~500MB+
  
  **Total: ~5.5GB minimum** when all components are active. A 4GB machine cannot run this system when Ollama is serving Gemma 4 2B. Even an 8GB machine would be under pressure during concurrent operations.
- **Impact**: Users following the "4GB+ RAM" guidance from ADR-013 will experience OOM errors when the full system runs.
- **Recommendation**: Update the minimum hardware requirement to 8GB RAM when using Ollama + local embeddings. Clarify that 4GB is sufficient for Ollama alone, but the full stack (embeddings + reranker + Ollama + PostgreSQL + Redis) requires significantly more. Add this as a key assumption in the system overview.

---

### Issue 4: Token Counting Wrong for Gemma 4 2B Context Window

- **Location**: `specs/004-context-and-synthesis/plan.md` lines 134-137, `specs/004-context-and-synthesis/notes.md` lines 23-30
- **Description**: Context construction uses `tiktoken` with `cl100k_base` encoding for token counting, explicitly noted as "(matches GPT-4o-mini tokenizer)." When the user selects Gemma 4 2B, this tokenizer produces incorrect counts:
  - Gemma uses a SentencePiece tokenizer, not BPE
  - A 4000-token context in `cl100k_base` could be significantly different in Gemma's tokenizer
  - Gemma 4 2B's context window size is not documented anywhere in the project
  
  The same context could be either too large (exceeding Gemma's limit) or too small (wasting available context window).
- **Impact**: When using Gemma 4 2B, context construction may produce prompts that exceed the model's input limit (truncated by Ollama, losing context) or underutilize available capacity.
- **Recommendation**: (a) Document Gemma 4 2B's context window size (8192 tokens), (b) either use model-specific tokenizers for context budgeting or document the approximation as acceptable, (c) add a safety margin (e.g., 3500 tokens for Gemma contexts).

---

### Issue 5: Ingestion Retry Creates Orphaned Chunks

- **Location**: `specs/001-document-ingestion/plan.md` lines 243-264, `adrs/009-single-worker-process.md` lines 22-23
- **Description**: ADR-009 states "if any stage fails, the entire job retries from the beginning." The processing flow (spec 001 plan) inserts chunks in Stage 7 (Persistence), then attempts to generate embeddings (spec 002). If embedding fails:
  1. Chunks are already in the database (INSERT completed)
  2. Job retries from text extraction
  3. New chunks are generated and inserted
  4. The original chunks from the failed attempt remain as orphans
  
  The `(document_id, chunk_index)` UNIQUE index would cause a duplicate key error on the second attempt's INSERT, causing the retry to fail immediately.
- **Impact**: Retry after embedding failure would always fail due to duplicate chunk records. The retry mechanism is effectively broken for post-persistence failures.
- **Recommendation**: Add a cleanup step at the start of job retry: DELETE all chunks for the document_id before re-processing. Alternatively, use UPSERT (INSERT ... ON CONFLICT DO UPDATE) for chunk persistence. Document this in spec 001 plan error handling section.

---

### Issue 6: No Startup Validation of Embedding Model vs Existing Data

- **Location**: `specs/002-embedding-and-storage/spec.md` FR-10 (line 22), `adrs/014-migrate-to-local-embedding-model.md` line 52
- **Description**: ADR-014 states: "The same model must be used for both chunk embeddings and query embeddings. Switching models requires re-embedding all existing chunks." However, there is no validation at application startup to verify that the configured `EMBEDDING_MODEL` matches the dimensionality of existing embeddings in the database. If an operator changes `EMBEDDING_MODEL=openai` to `EMBEDDING_MODEL=local` (or vice versa) without re-embedding, queries will produce meaningless results (768d query vectors compared against 1536d chunk vectors, or a pgvector dimension mismatch error).
- **Impact**: Silent retrieval quality degradation or runtime errors after a configuration change, with no warning or diagnostic message.
- **Recommendation**: Add a startup check: query the dimension of existing embeddings in the chunks table and compare against the configured model's output dimension. If mismatched, log a CRITICAL error and either refuse to start or operate in a degraded mode with a clear warning.

---

## Medium Priority Issues

### Issue 1: Migration Artifact — "API error" in Ingestion State Machine

- **Location**: `docs/architecture/system-overview.md` line 218
- **Description**: The ingestion state machine diagram contains `EmbeddingGeneration --> EmbeddingFailed: API error → retry`. Since embedding is now performed locally via `BAAI/bge-base-en-v1.5`, the label "API error" is a remnant of the OpenAI embedding model. This was missed during the ADR-014 migration.
- **Impact**: Misleading diagram for implementers; minor confusion about error source.
- **Recommendation**: Change to `EmbeddingGeneration --> EmbeddingFailed: Model inference error → retry`.

---

### Issue 2: Review Report Contains Wrong Model Tag in "New" Content

- **Location**: `specs/004-context-and-synthesis/review-report-e2b-to-ollama.md` line 123
- **Description**: The review report's Change 14 "New" section still contains `ollama pull gemma3:4b` in the proposed replacement text. The consistency-issue-resolution-report confirms MED-004 was resolved and `notes.md` was updated to `gemma4:2b`, but the review report's proposed content was not corrected.
- **Impact**: Minor — review reports are historical records, but this specific one shows incorrect "New" content that doesn't match what was actually applied.
- **Recommendation**: Update the review report's Change 14 "New" section to show `gemma4:2b` to match the actual applied content.

---

### Issue 3: Cross-Encoder Score Range Requires Verification

- **Location**: `specs/003-retrieval-pipeline/plan.md` line 66, `docs/architecture/system-overview.md` line 365, `adrs/012-remove-general-knowledge-fallback.md` line 14
- **Description**: Multiple documents state that the cross-encoder produces "confidence scores [0, 1]" and use 0.5 as the relevance threshold. The `cross-encoder/ms-marco-MiniLM-L-6-v2` model's raw output behavior depends on the `sentence-transformers` CrossEncoder class configuration. While the library typically applies sigmoid activation for single-label models (producing [0,1] output), this should be explicitly verified and documented, as the threshold's effectiveness depends entirely on the score distribution.
- **Impact**: If the score range assumption is wrong, the 0.5 threshold could be either too aggressive (filtering relevant results) or too permissive (passing irrelevant results).
- **Recommendation**: Add an explicit note in spec 003 plan and ADR-006 confirming that `CrossEncoder.predict()` applies sigmoid for this model, and document the expected score distribution. Consider adding a calibration step during testing to validate the threshold.

---

### Issue 4: No Ollama Model Availability Verification in Health Check

- **Location**: `specs/005-api-and-auth/plan.md` lines 155-173, `specs/005-api-and-auth/notes.md` lines 39-43
- **Description**: The health endpoint checks Ollama connectivity via `GET {OLLAMA_BASE_URL}/api/tags`, which verifies the Ollama service is running. However, it does not verify that the required `gemma4:2b` model is actually pulled and available. Ollama can be running with no models downloaded.
- **Impact**: The system reports Ollama as "healthy" but the first query using Gemma 4 2B fails with a model-not-found error, confusing users and operators.
- **Recommendation**: Enhance the Ollama health check to verify model availability by checking the response of `/api/tags` for the expected model name. Include model availability status in the health response.

---

### Issue 5: Gemma 4 2B Context Window Size Undocumented

- **Location**: `specs/004-context-and-synthesis/spec.md`, `specs/004-context-and-synthesis/plan.md`, `adrs/013-switch-from-e2b-to-ollama.md`
- **Description**: The context budget (~4000 tokens) and system prompt are designed with GPT-4o-mini's 128K context window in mind. Gemma 4 2B's context window is not documented anywhere. The model typically supports 8192 tokens, which is sufficient for the ~4000 token context + system prompt + query, but this should be stated explicitly.
- **Impact**: Without documented context limits, an implementer might not add appropriate safeguards for the smaller model, or might not realize that the token budget is safe for Gemma.
- **Recommendation**: Add Gemma 4 2B's context window size (8192 tokens) to ADR-013 and spec 004. Confirm the ~4000 token context + ~200 token overhead + ~100 token query fits within this limit.

---

### Issue 6: No Thread Safety Documentation for Shared Model Instances

- **Location**: `specs/002-embedding-and-storage/plan.md` lines 29-37, `specs/003-retrieval-pipeline/plan.md` lines 63-65
- **Description**: Both the embedding model and cross-encoder are loaded once at startup and shared across all requests/workers. The embedding model is used by both the ingestion worker (for chunk embeddings) and the query handler (for query embeddings) concurrently. The cross-encoder is used by concurrent query requests. No documentation addresses thread safety for these shared model instances.
- **Impact**: Concurrent access to `sentence-transformers` models is generally safe for inference (read-only forward passes), but without documentation, an implementer might add unnecessary locking or miss a real concurrency issue.
- **Recommendation**: Add a note to spec 002 plan and spec 003 plan confirming that `SentenceTransformer.encode()` and `CrossEncoder.predict()` are thread-safe for concurrent inference calls, and document the expected concurrency pattern (e.g., the embedding model may be called from both the arq worker and the FastAPI request handler simultaneously).

---

### Issue 7: No Documented Process for Re-Embedding After Model Switch

- **Location**: `adrs/014-migrate-to-local-embedding-model.md` line 52, `specs/002-embedding-and-storage/spec.md` "Out of Scope" line 56
- **Description**: ADR-014 states: "Switching models requires re-embedding all existing chunks." Spec 002 "Out of Scope" confirms: "Re-embedding existing chunks when switching models (requires document re-ingestion)." However, no spec, plan, or task describes how to actually trigger re-ingestion. There is no API endpoint for re-processing a document, no admin CLI tool, and no documented manual process.
- **Impact**: An operator who needs to switch embedding models (e.g., from local to OpenAI for quality testing) has no documented path to do so. They would need to: drop all chunks, drop and recreate the HNSW index, change the VECTOR column dimension, and re-upload all documents.
- **Recommendation**: Either (a) add a documented manual migration procedure to ADR-014, or (b) add a re-ingestion API endpoint to the Phase 1 backlog, or (c) add a management script to the Phase 1 tasks.

---

### Issue 8: No Formal Spec Dependency Graph

- **Location**: All spec files
- **Description**: Specs reference each other implicitly (e.g., spec 002 says "Requires chunks to be created first (spec 001)"; spec 003 says "output is passed to spec 004"), but there is no formal dependency graph documenting: which specs must be implemented in what order, which interfaces connect specs, and which shared resources (database tables, model instances) are owned by which spec.
- **Impact**: Implementation ordering mistakes — e.g., implementing spec 003 before spec 002's embedding model loader is available. Shared resource ownership ambiguity — e.g., who is responsible for loading the embedding model? Spec 002 plan shows the model loading pattern, but spec 003 also uses the model for query embedding.
- **Recommendation**: Add a dependency graph to the system overview or README showing: spec 001 → spec 002 → spec 003 → spec 004, with spec 005 (API layer) wrapping all, and spec 006 (observability) as cross-cutting. Document shared resource ownership (e.g., embedding model loaded by spec 002, used by specs 002 and 003).

---

### Issue 9: Document Deletion Not Supported Despite CASCADE Schema

- **Location**: `specs/001-document-ingestion/spec.md` "Out of Scope" line 64, `specs/001-document-ingestion/plan.md` line 182
- **Description**: The `chunks` table schema includes `REFERENCES documents(id) ON DELETE CASCADE`, indicating that deleting a document should cascade-delete its chunks. However, "Document deletion" is explicitly listed as out of scope. There is no DELETE API endpoint and no documented admin process for removing documents or sensitive data.
- **Impact**: Users cannot remove accidentally uploaded sensitive documents. The `ON DELETE CASCADE` constraint is implemented but unusable through any documented interface. For a system that emphasizes privacy (ADR-013, ADR-014), the inability to delete data is a notable gap.
- **Recommendation**: Either (a) add a `DELETE /api/v1/documents/{id}` endpoint to Phase 1 scope (leveraging the existing CASCADE constraint), or (b) document a manual SQL process for deletion, or (c) add a note explaining why deletion is deferred and when it will be addressed.

---

### Issue 10: No Request Cancellation for In-Flight Queries

- **Location**: `adrs/008-use-sse-streaming.md` lines 31-34, `specs/004-context-and-synthesis/spec.md` line 44
- **Description**: ADR-008 acknowledges that SSE is unidirectional: "cannot receive client messages during streaming (e.g., cancel request)." Spec 004 handles client disconnection (detect `ConnectionResetError`, cancel LLM call), but there is no proactive cancellation API. A long-running query (up to 120 seconds per SSE timeout) cannot be cancelled by the user except by closing the connection.
- **Impact**: Users who submit a query that takes a long time (e.g., slow Ollama inference) have no way to cancel and must wait or close the browser tab. For Phase 1 this is acceptable, but it should be documented as a known limitation.
- **Recommendation**: Document this as a known Phase 1 limitation in spec 004 or ADR-008. Consider adding a `DELETE /api/v1/query/{correlation_id}` cancellation endpoint to the Phase 2 roadmap.

---

## Low Priority Issues

### Issue 1: ADR-007 Tiktoken Rationale References OpenAI Models

- **Location**: `adrs/007-chunking-strategy.md` line 17
- **Description**: ADR-007 states: `Token counting: tiktoken with cl100k_base encoding (matches OpenAI models)`. The primary embedding model is no longer OpenAI. The rationale for the tokenizer choice is stale. The tokenizer is still used (for chunking and context budgeting), but its justification should reflect the current architecture.
- **Impact**: Minor confusion about why `cl100k_base` is used when the embedding model has a different tokenizer.
- **Recommendation**: Update the parenthetical to: `(used for consistent token counting across chunking and context construction; note: differs from embedding model tokenizer — see Critical Issue 3 in intensive review)`.

---

### Issue 2: Empty "Lessons Learned" Sections Across All Specs

- **Location**: All 6 spec `notes.md` files
- **Description**: Every spec's notes.md file contains `*(To be filled during implementation)*` in the Lessons Learned section. While expected pre-implementation, the Open Questions sections contain valuable unresolved questions (e.g., spec 001: "Should we support re-processing a failed document?", spec 002: "Should the model be downloaded automatically on first startup?") that affect implementation design.
- **Impact**: Open questions in notes.md may be overlooked during implementation since they aren't tracked as tasks or backlog items.
- **Recommendation**: Review all Open Questions across the 6 notes.md files and either resolve them (adding to spec/plan) or create explicit backlog items for decisions needed before or during implementation.

---

### Issue 3: Consistency Verification Report Baseline Data Is Pre-Migration

- **Location**: `docs/review-report/consistency-verification-report.md` lines 40-68
- **Description**: The existing consistency verification report's "Baseline: System Overview Key Facts" section lists `text-embedding-3-small (1536d)` as the embedding model and `1536` as embedding dimensions. This was accurate when the report was generated but is now outdated following the ADR-014 migration.
- **Impact**: A reader using the consistency verification report as a reference will see incorrect baseline values. The report's historical nature is not explicitly marked with a date or version.
- **Recommendation**: Add a dated header to the existing report (e.g., "Generated: [date], reflects state before ADR-014 embedding migration") to clarify its historical context.

---

### Issue 4: No ADR for Query Rewriting Model Selection Pattern

- **Location**: Implicit across `specs/003-retrieval-pipeline/spec.md` FR-2 and `specs/004-context-and-synthesis/spec.md` FR-5
- **Description**: The system has two distinct LLM operations with different model selection patterns: (1) query rewriting always uses GPT-4o-mini, (2) answer synthesis uses the user-selected model. This is an architectural decision that is not documented in any ADR. The rationale (GPT-4o-mini is better at instruction following for structured output) is implicit but never stated.
- **Impact**: Minor — the behavior is documented in the specs, just not formalized as an ADR decision.
- **Recommendation**: Consider adding a brief note to ADR-013 explaining why query rewriting remains on GPT-4o-mini even when the user selects Gemma 4 2B for synthesis.

---

### Issue 5: Plan Template Includes DELETE Endpoint Example

- **Location**: `specs/templates/plan.md` line 17
- **Description**: The plan template includes `DELETE /api/[endpoint-name]` as an example endpoint, but no spec implements a DELETE endpoint. Document deletion is explicitly out of scope for all Phase 1 specs.
- **Impact**: Cosmetic — template is a starting point, not prescriptive.
- **Recommendation**: No action needed. Template is appropriate as-is for general use.

---

### Issue 6: Query Rewrite Timeout Inconsistency

- **Location**: `specs/003-retrieval-pipeline/plan.md` line 149 vs `specs/003-retrieval-pipeline/spec.md` NFR-2 (line 27)
- **Description**: The error handling table specifies a 3-second timeout for query rewriting (`asyncio.TimeoutError after 3s`), but the NFR for query rewriting is "< 1.5 seconds." The timeout is 2× the target, which is reasonable as a safety margin, but the relationship between the target and the timeout is not documented.
- **Impact**: Minor — implementer might wonder why the timeout differs from the NFR.
- **Recommendation**: Add a brief note explaining the timeout is a safety margin above the NFR target.

---

## Implementation Risk Assessment

### High-Risk Areas

1. **Embedding model dimension handling**: The schema/fallback mismatch (Critical Issue 1) and tokenizer mismatch (Critical Issue 3) create a cluster of embedding-related risks. An implementer must understand three different dimension/tokenizer contexts (database schema, chunking, embedding model) and keep them consistent.

2. **Concurrent model access**: The embedding model is shared between the arq worker (ingestion) and FastAPI handler (query embedding). Without explicit documentation of the concurrency model, race conditions or deadlocks could emerge.

3. **Retry mechanism for ingestion**: The orphaned chunks issue (High Issue 5) means the first retry after any post-persistence failure will fail. This effectively reduces retry count from 3 to 1 for embedding failures.

4. **Offline operation mode**: The system claims offline capability but query rewriting breaks silently (Critical Issue 2, High Issue 2). An implementer needs to handle the full offline path explicitly.

5. **Memory management**: With ~640MB of ML models loaded at startup plus Ollama's ~4GB for Gemma, the system has a narrow operating margin on realistic hardware. Large PDF processing during concurrent queries could cause OOM.

### Missing Information

1. **Gemma 4 2B context window size** — affects context construction safety
2. **Cross-encoder exact score distribution** — affects threshold calibration
3. **Re-embedding migration procedure** — needed for any model switch
4. **Thread safety guarantees for sentence-transformers** — needed for concurrent access pattern
5. **Minimum hardware requirements** — current 4GB claim is insufficient
6. **Ollama model tag format** — `gemma4:2b` used in docs but not verified against Ollama registry

### Ambiguous Requirements

1. **"Optional fallback" for OpenAI embeddings** — Is this a runtime toggle or a deployment-time decision?
2. **Query rewriting model** — Is GPT-4o-mini always required, or should local rewriting be supported?
3. **Offline operation scope** — Which features work offline? Only LLM synthesis, or the full pipeline?
4. **Document re-processing** — Can a failed document be retried via API? (Open question in spec 001 notes)
5. **Embedding model auto-download** — Should the model download automatically on first startup? (Open question in spec 002 notes)

### Edge Cases Not Covered

1. **Mixed-dimension embeddings in database** — What happens if some chunks have 768d and others have 1536d embeddings (e.g., after a partial model switch)?
2. **Concurrent model switching** — What if `EMBEDDING_MODEL` is changed while an ingestion job is running?
3. **Ollama model version updates** — What happens if the user updates the Gemma model in Ollama? Does this affect answer quality or reproducibility?
4. **Empty database queries** — The "no documents indexed" case is handled, but what about partially indexed documents (status = processing)?
5. **Very large chunk counts** — A 50MB PDF could produce 1000+ chunks. Batch embedding at ~50ms/chunk = 50 seconds, exceeding the 30-second ingestion target.

---

## Design Consistency Analysis

### Cross-Spec Dependencies

| Spec | Depends On | Provides To | Shared Resources |
|------|-----------|-------------|-----------------|
| 001 (Ingestion) | — | 002, 003 (chunks table) | PostgreSQL, Redis, filesystem |
| 002 (Embedding) | 001 (chunks) | 003 (embeddings, HNSW index) | Embedding model instance, PostgreSQL |
| 003 (Retrieval) | 002 (embeddings), 001 (chunks) | 004 (ranked chunks) | Embedding model, cross-encoder model |
| 004 (Synthesis) | 003 (ranked chunks) | — (SSE output) | Ollama client, OpenAI client |
| 005 (API/Auth) | — | All specs (API layer) | Config, auth middleware |
| 006 (Observability) | — | All specs (logging) | Logging infrastructure |

**Gap identified**: Specs 002 and 003 both use the embedding model but ownership is ambiguous. Spec 002 plan shows the model loading pattern; spec 003 plan's internal interface accepts `embedding_model: SentenceTransformer` as a parameter. Neither spec explicitly owns model lifecycle management. This should be clarified — recommend spec 002 owns model loading and exposes it via dependency injection.

### ADR Consistency

- **ADR supersession chain is clean**: ADR-004 → ADR-014, ADR-011 → ADR-013. All references updated.
- **ADR-007 tokenizer rationale is stale** (Low Issue 1) but ADR itself is technically still correct.
- **No circular or conflicting ADR decisions detected**.
- **ADR coverage gap**: No ADR for the dual-model pattern (GPT-4o-mini for rewriting, user-selected for synthesis).

### Architecture Alignment

- **System overview ↔ Specs**: Generally aligned after previous consistency fixes. One remaining contradiction (High Issue 1: retry behavior).
- **System overview ↔ ADRs**: Aligned after embedding migration. One migration artifact (Medium Issue 1: "API error" label).
- **Privacy architecture**: Fundamentally inconsistent — local-first claims (ADR-013, ADR-014) are undermined by mandatory OpenAI query rewriting (Critical Issue 2).
- **Offline architecture**: Partially broken — system overview claims offline capability but query pipeline requires internet for rewriting.

---

## Recommendations

### Before Implementation

1. **Resolve OpenAI embedding fallback architecture** (Critical Issue 1) — Decide: remove from Phase 1 or document full migration process
2. **Resolve privacy gap in query rewriting** (Critical Issue 2) — Decide: local rewriting, single-query degradation, or documented limitation
3. **Address tokenizer mismatch** (Critical Issue 3) — Add validation or reduce chunk size
4. **Fix retry behavior contradiction** (High Issue 1) — Align system overview with ADR-009
5. **Add chunk cleanup on retry** (High Issue 5) — Prevent orphaned chunks breaking retries
6. **Update minimum hardware requirements** (High Issue 3) — Change from 4GB to 8GB+
7. **Fix "API error" migration artifact** (Medium Issue 1) — Simple text change

### During Implementation

8. **Add startup embedding dimension validation** (High Issue 6)
9. **Add Ollama model availability check** (Medium Issue 4)
10. **Verify cross-encoder score range** (Medium Issue 3) — Test during integration
11. **Document thread safety model** (Medium Issue 6)
12. **Implement token counting safety margin** for Gemma 4 2B (High Issue 4)
13. **Resolve all Open Questions** in spec notes.md files (Low Issue 2)

### Future Improvements

14. **Add document deletion API** (Medium Issue 9)
15. **Add re-embedding management tool** (Medium Issue 7)
16. **Add request cancellation endpoint** (Medium Issue 10)
17. **Add formal spec dependency graph** (Medium Issue 8)
18. **Create ADR for query rewriting model pattern** (Low Issue 4)

---

## Conclusion

The AI Research Workspace RAG system documentation is well-structured and has benefited significantly from prior consistency reviews and migrations. However, this intensive review uncovered **3 critical issues** that must be resolved before implementation:

1. The OpenAI embedding fallback is architecturally broken at the database schema level
2. The privacy-first architecture is violated by mandatory OpenAI query rewriting
3. The tokenizer mismatch between chunking and embedding risks silent information loss

These issues stem from the recent embedding model migration (ADR-014), which updated dimensions, model references, and storage consistently but did not fully address the architectural implications of switching from an API-based to a local model (tokenizer differences, fallback feasibility, privacy scope).

The 6 high-priority issues relate to implementation risks that could cause runtime failures (orphaned chunks on retry, memory pressure, missing validation) and should be addressed early in the implementation phase.

The project is **not yet ready for implementation** until the 3 critical issues are resolved. Once addressed, the architecture is sound and the documentation quality is high — significantly above average for a pre-implementation project.

---

*Report generated: Intensive project-wide implementation risk assessment*
*Scope: All ADRs (001–014), all specs (001–006), all templates, all review/migration reports, system overview, README*
*Method: Full file-by-file reading of every .md file in the project, cross-document analysis, implementer perspective*
*Prior context: Builds on the consistency verification report (above) and the consistency issue resolution report*
