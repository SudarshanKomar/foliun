# ADR-006: Use cross-encoder/ms-marco-MiniLM-L-6-v2 for Reranking

## Status
Accepted

## Context
Vector similarity search (bi-encoder) retrieves candidate chunks efficiently but with limited accuracy. Bi-encoders encode query and document independently, missing fine-grained query-document interactions. A reranking step using a cross-encoder model can significantly improve precision by jointly encoding the (query, document) pair.

The reranker must run on CPU (no GPU infrastructure in Phase 1), score 30 candidates in < 1.5 seconds (sequential inference, ~50ms per pair), and produce calibrated confidence scores for relevance thresholding.

Candidates considered: `cross-encoder/ms-marco-MiniLM-L-6-v2`, `cross-encoder/ms-marco-MiniLM-L-12-v2`, `BAAI/bge-reranker-v2-m3`, Cohere Rerank API.

## Decision
We will use **`cross-encoder/ms-marco-MiniLM-L-6-v2`** for reranking, hosted in-process via the `sentence-transformers` library.

- Model loaded once at application startup, kept in memory
- Reranks top 30 candidates from RRF fusion
- Scores each (original_query, chunk_text) pair
- Selects top 10 by cross-encoder confidence score
- Relevance threshold: cross-encoder confidence > 0.5
- **Critical**: reranking uses the **original user query**, not rewritten variants

## Consequences

### Positive
- Significant precision improvement over bi-encoder-only retrieval (10-20% improvement in NDCG@10 on MS MARCO)
- 6-layer model is fast on CPU: ~50ms per (query, chunk) pair, ~1.5s for 30 candidates
- Small model size (~80MB), fits easily in memory
- Well-benchmarked on MS MARCO passage ranking — proven for document Q&A use case
- Open-source, no API costs, no external dependencies
- Calibrated output scores [0, 1] enable reliable relevance thresholding

### Negative
- CPU-bound computation blocks the async event loop; must run in thread pool executor
- Memory footprint (~200MB with model + tokenizer) per process
- Single-threaded inference — limits concurrency for query processing
- 12-layer variant (`L-12-v2`) offers better accuracy but doubles latency (~100ms/pair)

### Neutral
- Model is loaded from HuggingFace Hub on first run, then cached locally
- The 0.5 relevance threshold may need calibration based on real-world query patterns
- Can be replaced with a Cohere Rerank API call for reduced latency but added cost

## Related ADRs
- ADR-005: Use Reciprocal Rank Fusion for multi-query score merging
- ADR-012: Remove general knowledge fallback
