# Retrieval Pipeline Notes

## Research Links
- [Reciprocal Rank Fusion (Cormack et al., 2009)](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf) — Original RRF paper, k=60 recommendation
- [MS MARCO Passage Ranking](https://microsoft.github.io/msmarco/) — Benchmark dataset for cross-encoder evaluation
- [sentence-transformers CrossEncoder](https://www.sbert.net/docs/cross_encoder/usage/usage.html) — Python library for cross-encoder inference
- [Multi-Query Retrieval](https://python.langchain.com/docs/how_to/MultiQueryRetriever/) — LangChain implementation reference
- [pgvector distance operators](https://github.com/pgvector/pgvector#querying) — `<=>` cosine distance, `<->` L2 distance

## Design Discussions

### Why Multi-Query + RRF + Reranking (Three-Stage Pipeline)?
A single vector search with one query often misses relevant chunks because:
1. User queries may use different vocabulary than the document text
2. Embedding models may not capture the query's full semantic intent in a single vector

Multi-query addresses this by searching with diverse query formulations. RRF merges results robustly. Cross-encoder reranking then refines precision by jointly encoding (query, document) pairs — something bi-encoder search cannot do.

This three-stage approach is standard in production RAG systems (e.g., Anthropic's documentation search, Cohere's RAG pipeline).

### Why Original Query for Reranking?
Rewritten queries are optimized for retrieval diversity (broader recall). But reranking should measure relevance to the user's actual intent. The original query best represents user intent, so the cross-encoder scores each chunk against the original query, not the rewritten variants.

### RRF k=60 vs Other Values
The original RRF paper (Cormack et al., 2009) recommends k=60 as a robust default. Lower k values (e.g., k=1) heavily favor top-ranked items; higher k values (e.g., k=1000) treat all ranks almost equally. k=60 provides a good balance where top-ranked items get meaningful boost but lower-ranked items still contribute.

We use k=60 as-is. Tuning k requires a labeled evaluation dataset, which is deferred to Phase 2.

### Cross-Encoder on CPU vs GPU
The `ms-marco-MiniLM-L-6-v2` model (6 layers, 22M parameters) runs efficiently on CPU:
- ~50ms per (query, chunk) pair
- ~1.5s for 30 pairs (sequential)
- ~200MB memory footprint

GPU inference would reduce this to ~5ms per pair but requires GPU infrastructure. For Phase 1's concurrency target (10+ concurrent queries), CPU is the bottleneck. Mitigation: limit reranking to 30 candidates, implement 2-second timeout, and fall back to RRF-only if timeout hit.

### Why Top 20 per Query (Not 50)?
The original design proposed 50 chunks per query (150 total candidates). This was reduced to 20 per query (80 total) because:
1. Cross-encoder reranking costs scale linearly with candidates
2. RRF with 4 diverse queries provides sufficient recall with 20 per query
3. Beyond position 20, cosine similarity scores drop significantly — lower-ranked chunks are rarely relevant
4. 80 unique candidates → 30 after RRF top selection → 10 after reranking is a clean funnel

### Thread Pool for Cross-Encoder
Cross-encoder inference is CPU-bound (forward pass through transformer model). Running it in the async event loop would block all concurrent requests. We run inference in `asyncio.loop.run_in_executor()` with a thread pool. The GIL limits true parallelism, but this at least unblocks the event loop for other async operations (database queries, SSE streaming).

## Lessons Learned
*(To be filled during implementation)*

## Open Questions
- Should we cache query rewriting results for identical queries?
- Should we implement a query cache for repeated vector searches?
- How should we handle queries in languages other than English? (Phase 1 assumes English only)
- Should we log the full rewriting prompt and response for debugging, or just the variants?
- Would pre-filtering by document ID (user-selected scope) improve retrieval quality?
