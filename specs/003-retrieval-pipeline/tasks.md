# Retrieval Pipeline Implementation Tasks

## Phase 1: Foundation
- [ ] Install sentence-transformers library and verify cross-encoder model downloads (estimate: 1h)
- [ ] Implement cross-encoder model loader: load at startup, cache in memory (estimate: 1.5h)
- [ ] Create retrieval data classes: RankedChunk, RetrievalResult, RetrievalMetadata (estimate: 1h)
- [ ] Set up asyncio thread pool executor for CPU-bound cross-encoder inference (estimate: 1h)
- [ ] Configure pgvector session parameter: `SET hnsw.ef_search = 40` at connection level (estimate: 0.5h)

## Phase 2: Core Implementation
- [ ] Implement query rewriter: GPT-4o-mini prompt to generate 3 diverse query variants (estimate: 2h)
- [ ] Implement query rewriter output parser: split response into individual queries, handle malformed output (estimate: 1h)
- [ ] Implement query rewriter graceful degradation: on failure, use original query only with warning log (estimate: 1h)
- [ ] Implement query embedding: embed 4 queries in single OpenAI API call (estimate: 1.5h)
- [ ] Implement parallel vector search: 4 concurrent pgvector queries via asyncio.gather() (estimate: 3h)
- [ ] Implement pgvector cosine similarity query with document status filter (estimate: 1.5h)
- [ ] Implement RRF score fusion: deduplicate by (document_id, chunk_index), compute RRF scores with k=60 (estimate: 2h)
- [ ] Implement cross-encoder reranking: prepare (query, chunk) pairs, run inference in thread pool (estimate: 3h)
- [ ] Implement cross-encoder timeout: cancel after 2 seconds, fall back to RRF-only ranking (estimate: 1h)
- [ ] Implement relevance threshold check: flag insufficient_context if max score < 0.5 (estimate: 0.5h)
- [ ] Implement top-K selection: select top 10 chunks from reranked results (estimate: 0.5h)
- [ ] Wire up full pipeline orchestrator: rewrite → embed → search → RRF → rerank → return (estimate: 2h)
- [ ] Add stage latency tracking to RetrievalMetadata (estimate: 1h)

## Phase 3: Testing & Refinement
- [ ] Unit test: RRF algorithm — verify scores for known rank inputs, deduplication, k=60 behavior (estimate: 2h)
- [ ] Unit test: query rewriter output parsing — valid output, malformed output, empty output (estimate: 1h)
- [ ] Unit test: relevance threshold — chunks above/below 0.5, empty result set (estimate: 1h)
- [ ] Unit test: graceful degradation — rewriter failure, reranker failure, both failures (estimate: 2h)
- [ ] Integration test: full retrieval pipeline with real embeddings and cross-encoder (estimate: 3h)
- [ ] Integration test: parallel vector search returns correct results across 4 queries (estimate: 2h)
- [ ] Integration test: query with no relevant documents returns insufficient_context=true (estimate: 1h)
- [ ] Performance test: retrieval pipeline latency < 4 seconds on typical queries (estimate: 1.5h)
- [ ] Performance test: cross-encoder reranking < 500ms for 30 candidates (estimate: 1h)
- [ ] Manual relevance test: compare single-query vs multi-query retrieval on 10 test queries (estimate: 2h)

## Phase 4: Documentation & Cleanup
- [ ] Document query rewriting prompt and expected output format (estimate: 0.5h)
- [ ] Document RRF algorithm with examples (estimate: 1h)
- [ ] Document cross-encoder model loading and memory requirements (estimate: 0.5h)
- [ ] Document graceful degradation behavior and fallback chain (estimate: 0.5h)
