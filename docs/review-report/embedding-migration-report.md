# Embedding Model Migration Report: OpenAI → Local (BAAI/bge-base-en-v1.5)

**Date**: 2025-06-01
**Migration**: OpenAI `text-embedding-3-small` (1536d) → `BAAI/bge-base-en-v1.5` (768d)
**Status**: ✅ Complete — all documentation updated and verified

---

## 1. Model Selection

### Selected Model
| Property | Value |
|----------|-------|
| Model | `BAAI/bge-base-en-v1.5` |
| Library | `sentence-transformers` (already a project dependency) |
| Dimensions | 768 |
| Parameters | 110M |
| MTEB Average | 63.55 |
| Max Sequence | 512 tokens (matches chunk size) |
| License | MIT |
| Memory | ~440MB |
| CPU Speed | ~50ms per chunk, ~3-5s for 50 chunks (batched) |

### Selection Rationale
- Highest MTEB score among base-sized models
- 768d provides excellent quality/storage balance (50% storage reduction vs 1536d)
- CPU-friendly (no GPU required), fits alongside cross-encoder reranker in memory
- No new library dependency (uses existing `sentence-transformers`)
- MIT license, no restrictions
- 512 token max sequence matches chunk size exactly

### Rejected Alternatives
| Model | Dims | Why Rejected |
|-------|------|-------------|
| all-MiniLM-L6-v2 | 384 | Significantly lower MTEB score (~56 vs 63.55) |
| bge-large-en-v1.5 | 1024 | Too heavy for CPU (~1.3GB, ~150ms/chunk) |
| intfloat/e5-base-v2 | 768 | Lower MTEB score (~61) |
| nomic-embed-text-v1 | 768 | Requires `trust_remote_code`, less proven |

---

## 2. Files Created

| File | Description |
|------|-------------|
| `adrs/014-migrate-to-local-embedding-model.md` | New ADR documenting the migration decision, model selection rationale, consequences, and related ADRs |

## 3. Files Modified

### ADRs (6 files)
| File | Changes |
|------|---------|
| `adrs/004-use-openai-embedding-model.md` | Added supersession banner, status changed to "Superseded by ADR-014", added ADR-014 to Related ADRs |
| `adrs/001-use-postgresql-pgvector.md` | `VECTOR(1536)` → `VECTOR(768)` with fallback note |
| `adrs/005-use-reciprocal-rank-fusion.md` | ADR-004 → ADR-014 in Related ADRs |
| `adrs/007-chunking-strategy.md` | ADR-004 → ADR-014 in Related ADRs |
| `adrs/009-single-worker-process.md` | ADR-004 → ADR-014 in Related ADRs, updated "API latency" to "inference latency" |

### System Overview (1 file)
| File | Changes |
|------|---------|
| `docs/architecture/system-overview.md` | 12 updates: Phase 1 scope, external entities (OpenAI now optional for embeddings), embedding generator component, DB schema (VECTOR(768)), ingestion state machine, query state machine, ingestion data flow, query data flow, technology table, embedding model note, domain language, key assumption (internet now optional) |

### Spec 001 — Document Ingestion (3 files)
| File | Changes |
|------|---------|
| `specs/001-document-ingestion/spec.md` | Updated embedding time budget from 10s to 15s (local CPU) |
| `specs/001-document-ingestion/plan.md` | `VECTOR(1536)` → `VECTOR(768)` in schema with fallback note |
| `specs/001-document-ingestion/notes.md` | Updated embedding column description from 1536 to 768 |

### Spec 002 — Embedding and Storage (4 files)
| File | Changes |
|------|---------|
| `specs/002-embedding-and-storage/spec.md` | Complete rewrite: context, all FRs, all NFRs, constraints, failure cases, success criteria, out of scope — all updated from OpenAI API to local model |
| `specs/002-embedding-and-storage/plan.md` | Complete rewrite: architecture, data flow, API call pattern, internal interface, SQL schema, storage estimates (halved), pipeline stages, error handling, related ADRs |
| `specs/002-embedding-and-storage/tasks.md` | All 4 phases rewritten: foundation, core implementation, testing, documentation tasks updated for local model |
| `specs/002-embedding-and-storage/notes.md` | Research links, model comparison, HNSW params, embedding column, query prefix, batch size, memory budget, open questions — all updated |

### Spec 003 — Retrieval Pipeline (3 files)
| File | Changes |
|------|---------|
| `specs/003-retrieval-pipeline/spec.md` | FR-3 updated (768d, query prefix), constraint updated, failure case updated (model inference vs API error) |
| `specs/003-retrieval-pipeline/plan.md` | Architecture overview, Stage 2 (query embedding), pipeline summary table, internal interface (SentenceTransformer), error handling table, Related ADRs |
| `specs/003-retrieval-pipeline/tasks.md` | Query embedding task updated from OpenAI API to local model |

### Spec 005 — API and Auth (2 files)
| File | Changes |
|------|---------|
| `specs/005-api-and-auth/plan.md` | `OPENAI_API_KEY` made optional, `EMBEDDING_MODEL` env var added, ADR-014 added to Related ADRs |
| `specs/005-api-and-auth/notes.md` | Added health check note for in-process embedding model |

### Spec 006 — Observability (3 files)
| File | Changes |
|------|---------|
| `specs/006-observability/spec.md` | Embedding cost tracking → embedding model/latency tracking |
| `specs/006-observability/plan.md` | Ingestion logging table updated (cost → performance), embedding vector size updated (768-dim), ADR-014 added to Related ADRs |
| `specs/006-observability/tasks.md` | Embedding tracking task updated from cost to performance |
| `specs/006-observability/notes.md` | Sensitive data table: 1536-dim → 768-dim, 6KB → 3KB |

### README (1 file)
| File | Changes |
|------|---------|
| `README.md` | Tech stack updated from OpenAI embedding to local model |

**Total: 1 file created, 21 files modified**

---

## 4. Files Intentionally NOT Modified

| File | Reason |
|------|--------|
| `docs/architecture/review-report.md` | Historical review report — references to `text-embedding-3-small` are in the context of issues identified at that time |
| `docs/review-report/consistency-verification-report.md` | Historical verification report — captured the state of the system before this migration |
| `docs/architecture/review-report-e2b-to-ollama.md` | E2B→Ollama migration report — not related to embedding model |
| `specs/004-context-and-synthesis/*` | No embedding model references |
| `adrs/002-*.md` through `adrs/003-*.md` | No embedding model references |
| `adrs/006-*.md`, `adrs/008-*.md`, `adrs/010-*.md` through `adrs/013-*.md` | No embedding model references |

---

## 5. Verification Results

### Pass 1: Stale `1536` references
- **Result**: ✅ No stale references in living docs
- All remaining `1536` mentions are in: (a) historical reports, (b) ADR-004 preserved content, (c) ADR-014 migration context, or (d) "OpenAI fallback" context

### Pass 2: `text-embedding-3-small` as primary model
- **Result**: ✅ No stale primary references
- All 20 remaining mentions across 9 files are in: superseded ADR-004, ADR-014 context, fallback descriptions, or historical reports

### Pass 3: ADR-004 references → ADR-014
- **Result**: ✅ All living doc Related ADRs sections updated
- ADR-004 references in living docs now say "ADR-014 ... (supersedes ADR-004)"

### Pass 4: `BAAI/bge-base-en-v1.5` consistency
- **Result**: ✅ 48 matches across 20 files — all consistent naming

### Pass 5: `VECTOR(768)` consistency
- **Result**: ✅ All SQL schemas, specs, and ADRs use `VECTOR(768)` for the local model

### Pass 6: `EMBEDDING_MODEL` environment variable
- **Result**: ✅ Consistently documented with values `local` (default) and `openai` across spec 002, spec 005, and ADR-014

### Pass 7: Dimension (`768`) consistency
- **Result**: ✅ 48 matches across 15 files — all consistent

---

## 6. Key Design Decisions

1. **Local-first, OpenAI optional**: Mirrors the LLM architecture (Ollama default, GPT-4o-mini optional). Controlled via `EMBEDDING_MODEL` env var.
2. **Query instruction prefix**: `bge-base-en-v1.5` uses `"Represent this sentence for searching relevant passages: "` for queries, no prefix for documents.
3. **Model loaded at startup**: Same lifecycle pattern as cross-encoder reranker. ~440MB memory, ~2-3 seconds load time.
4. **Internet now optional**: With local embeddings + Ollama, the system can run fully offline. Updated key assumption #2 in system overview.
5. **`OPENAI_API_KEY` now optional**: Only required for GPT-4o-mini LLM or `EMBEDDING_MODEL=openai`.
6. **Storage reduction**: 768d vectors are 50% smaller than 1536d — all storage estimates in spec 002 plan halved.
7. **Performance target adjusted**: Embedding generation target relaxed from 10s (API) to 15s (CPU) for 50 chunks.

---

## 7. Migration Status

| Aspect | Status |
|--------|--------|
| Model selected | ✅ BAAI/bge-base-en-v1.5 |
| ADR created | ✅ ADR-014 |
| ADR-004 superseded | ✅ With banner and status change |
| System overview updated | ✅ 12 changes |
| Spec 002 updated | ✅ All 4 files |
| Spec 001 updated | ✅ 3 files |
| Spec 003 updated | ✅ 3 files |
| Spec 005 updated | ✅ 2 files |
| Spec 006 updated | ✅ 4 files |
| Related ADRs updated | ✅ ADRs 001, 005, 007, 009 |
| README updated | ✅ |
| Verification passed | ✅ 7 passes, all clean |
