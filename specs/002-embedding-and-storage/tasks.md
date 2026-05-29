# Embedding and Storage Implementation Tasks

## Phase 1: Foundation
- [ ] Install and configure pgvector extension in PostgreSQL (estimate: 1h)
- [ ] Add pgvector HNSW index migration for `chunks.embedding` column (estimate: 1h)
- [ ] Set up OpenAI Python SDK with async client (`openai.AsyncOpenAI`) (estimate: 1h)
- [ ] Create embedding configuration: model name, batch size, timeout, retry settings as environment variables (estimate: 1h)

## Phase 2: Core Implementation
- [ ] Implement `generate_embeddings()` function: batch text inputs, call OpenAI API, return vectors (estimate: 3h)
- [ ] Implement batch splitting logic: split chunk lists into groups of ≤ 2048 for API calls (estimate: 1h)
- [ ] Implement `store_embeddings()` function: batch UPDATE chunks table with embedding vectors (estimate: 2h)
- [ ] Integrate embedding stage into arq worker job: call after chunking, before status update (estimate: 2h)
- [ ] Implement OpenAI rate limit handling: parse `Retry-After` header, wait, and retry (estimate: 1.5h)
- [ ] Implement exponential backoff retry wrapper for OpenAI API calls (1s, 4s, 16s) (estimate: 1h)
- [ ] Implement embedding count verification: ensure all chunks have non-NULL embeddings before marking `ready` (estimate: 1h)
- [ ] Add cost tracking log entry per document: total tokens, estimated USD cost (estimate: 0.5h)
- [ ] Configure `ef_search` session parameter for query-time performance (estimate: 0.5h)

## Phase 3: Testing & Refinement
- [ ] Unit test: batch splitting — verify correct grouping for 1, 100, 2048, 3000 chunks (estimate: 1h)
- [ ] Unit test: embedding dimension validation — verify all vectors are exactly 1536 dimensions (estimate: 0.5h)
- [ ] Integration test: generate embeddings for real chunks via OpenAI API and store in pgvector (estimate: 2h)
- [ ] Integration test: verify HNSW index is functional — insert vectors, query with cosine similarity, verify results (estimate: 2h)
- [ ] Integration test: simulate OpenAI API failure — verify retry behavior and final failure handling (estimate: 2h)
- [ ] Integration test: simulate rate limit (429) — verify Retry-After handling (estimate: 1h)
- [ ] Performance test: measure HNSW query latency at 1K, 10K, 100K vectors (estimate: 2h)
- [ ] Performance test: measure embedding generation time for 50 chunks (target: < 10s) (estimate: 1h)
- [ ] Verify end-to-end: upload PDF → chunks created → embeddings generated → document ready (estimate: 1h)

## Phase 4: Documentation & Cleanup
- [ ] Document pgvector HNSW index parameters and tuning guidance (estimate: 1h)
- [ ] Document OpenAI API cost model and monitoring approach (estimate: 0.5h)
- [ ] Add health check for OpenAI API connectivity (estimate: 0.5h)
