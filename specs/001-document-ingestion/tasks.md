# Document Ingestion Implementation Tasks

## Phase 1: Foundation
- [ ] Create project skeleton: FastAPI app, config, database connection (estimate: 3h)
- [ ] Set up PostgreSQL with pgvector extension enabled (estimate: 1h)
- [ ] Create `documents` table migration with all columns and indexes (estimate: 1h)
- [ ] Create `chunks` table migration with all columns and indexes (embedding column nullable) (estimate: 1h)
- [ ] Set up arq worker with Redis connection and basic job handler (estimate: 2h)
- [ ] Create `./storage/documents/` directory structure with proper permissions (estimate: 0.5h)
- [ ] Set up BERT WordPiece tokenizer from `BAAI/bge-base-en-v1.5` via `transformers.AutoTokenizer` for token counting (estimate: 0.5h)

## Phase 2: Core Implementation
- [ ] Implement file validation middleware: MIME type check (PDF, TXT), size check (≤50MB), empty check (estimate: 2h)
- [ ] Implement SHA-256 file hashing and duplicate detection query (estimate: 1h)
- [ ] Implement `POST /api/v1/documents` endpoint: validate → store file → create DB record → enqueue job → return 202 (estimate: 3h)
- [ ] Implement `GET /api/v1/documents/{id}/status` endpoint with chunk count aggregation (estimate: 1h)
- [ ] Implement `GET /api/v1/documents` endpoint with status and chunk count (estimate: 1h)
- [ ] Implement PDF text extraction using PyMuPDF: page iteration, text extraction, page-to-offset mapping (estimate: 3h)
- [ ] Implement TXT file reading with UTF-8 encoding and basic validation (estimate: 1h)
- [ ] Implement recursive character text splitter: separator hierarchy, token-based sizing, overlap (estimate: 4h)
- [ ] Implement metadata enrichment: page number mapping, section header detection, character offsets (estimate: 3h)
- [ ] Implement chunk batch INSERT to PostgreSQL (estimate: 1.5h)
- [ ] Implement ingestion worker job handler: cleanup existing chunks → extraction → chunking → enrichment → persistence → status update (estimate: 3h)
- [ ] Implement chunk cleanup on retry: `DELETE FROM chunks WHERE document_id = :doc_id` before re-processing to prevent orphaned data (estimate: 0.5h)
- [ ] Implement document status transitions (pending → processing → ready/failed) with updated_at timestamps (estimate: 1h)
- [ ] Implement filename sanitization (remove path traversal characters) (estimate: 0.5h)

## Phase 3: Testing & Refinement
- [ ] Create test fixtures: 1-page PDF, 10-page PDF, 100-page PDF, small TXT, large TXT, empty file, corrupted PDF (estimate: 2h)
- [ ] Unit test: file validation (type, size, empty) with valid and invalid inputs (estimate: 2h)
- [ ] Unit test: recursive character text splitter — chunk sizes, overlap, separator behavior (estimate: 3h)
- [ ] Unit test: metadata enrichment — page number mapping, section header detection (estimate: 2h)
- [ ] Unit test: duplicate detection — same file, different file same name, same file different name (estimate: 1h)
- [ ] Integration test: full upload → status → ready flow with real PDF (estimate: 3h)
- [ ] Integration test: upload failure scenarios (invalid type, too large, corrupted PDF) (estimate: 2h)
- [ ] Integration test: retry behavior — simulate extraction failure, verify 3 retries with backoff (estimate: 2h)
- [ ] Performance test: verify 10-page PDF ingestion completes in < 30 seconds (estimate: 1h)
- [ ] Verify chunk size distribution: mean between 460-564 tokens (estimate: 1h)

## Phase 4: Documentation & Cleanup
- [ ] Document API endpoints in OpenAPI schema with examples (estimate: 1h)
- [ ] Add structured logging to all pipeline stages (estimate: 1.5h)
- [ ] Add configuration for file size limit, chunk size, overlap, storage path via environment variables (estimate: 1h)
- [ ] Review and clean up error messages for consistency (estimate: 0.5h)
