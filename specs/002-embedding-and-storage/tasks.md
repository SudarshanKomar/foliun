# Embedding and Storage Implementation Tasks

## Phase 1: Foundation
- [ ] Install and configure pgvector extension in PostgreSQL (estimate: 1h)
- [ ] Add pgvector HNSW index migration for `chunks.embedding` column — VECTOR(768) (estimate: 1h)
- [ ] Set up `sentence-transformers` library and verify `BAAI/bge-base-en-v1.5` model downloads (estimate: 1h)
- [ ] Implement embedding model loader: load at startup, cache in memory (~440MB), log load time (estimate: 1.5h)
- [ ] Create embedding configuration: model name, batch size, retry settings (estimate: 1h)

## Phase 2: Core Implementation
- [ ] Implement `generate_embeddings()` function: encode texts locally via `model.encode()`, return 768d vectors (estimate: 2h)
- [ ] Implement query instruction prefix logic: prepend `"Represent this sentence for searching relevant passages: "` for queries (estimate: 0.5h)
- [ ] Implement `store_embeddings()` function: batch UPDATE chunks table with embedding vectors (estimate: 2h)
- [ ] Integrate embedding stage into arq worker job: call after chunking, before status update (estimate: 2h)
- [ ] Implement exponential backoff retry wrapper for embedding inference failures (1s, 4s, 16s) (estimate: 1h)
- [ ] Implement embedding count verification: ensure all chunks have non-NULL embeddings before marking `ready` (estimate: 1h)
- [ ] Add performance tracking log entry per document: chunks, model name, latency_ms (estimate: 0.5h)
- [ ] Configure `ef_search` session parameter for query-time performance (estimate: 0.5h)
- [ ] Implement startup validation: verify model outputs 768d vectors and existing DB embeddings are compatible (estimate: 1h)

## Phase 3: Testing & Refinement
- [ ] Unit test: embedding dimension validation — verify all vectors are exactly 768 dimensions (estimate: 0.5h)
- [ ] Unit test: query instruction prefix — verify prefix applied for queries, not for documents (estimate: 0.5h)
- [ ] Integration test: generate embeddings for real chunks via local model and store in pgvector (estimate: 2h)
- [ ] Integration test: verify HNSW index is functional — insert 768d vectors, query with cosine similarity, verify results (estimate: 2h)
- [ ] Integration test: verify model loads at startup in < 10 seconds (estimate: 0.5h)
- [ ] Integration test: simulate embedding inference failure — verify retry behavior and final failure handling (estimate: 1.5h)
- [ ] Performance test: measure HNSW query latency at 1K, 10K, 100K vectors (estimate: 2h)
- [ ] Performance test: measure embedding generation time for 50 chunks on CPU (target: < 15s) (estimate: 1h)
- [ ] Verify end-to-end: upload PDF → chunks created → embeddings generated → document ready (estimate: 1h)

## Phase 4: Documentation & Cleanup
- [ ] Document pgvector HNSW index parameters and tuning guidance (estimate: 1h)
- [ ] Document embedding model selection rationale and CPU performance characteristics (estimate: 0.5h)
- [ ] Document embedding model configuration and startup validation behavior (estimate: 0.5h)
- [ ] Add health check for embedding model availability at startup (estimate: 0.5h)
