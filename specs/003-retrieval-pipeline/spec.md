# Retrieval Pipeline Specification

## Context
The retrieval pipeline is the core read-path of the RAG system. When a user submits a query, the system must find the most relevant document chunks from the vector store. Retrieval quality is the single most important factor in answer quality — if the wrong chunks are retrieved, no amount of LLM sophistication can produce a good answer.

This spec covers the full retrieval pipeline: query rewriting (multi-query generation), query embedding, parallel vector search, Reciprocal Rank Fusion (RRF) for score merging, and cross-encoder reranking. The output is a ranked list of the top 10 most relevant chunks, ready for context construction (spec 004).

The pipeline is designed for high recall (multi-query expansion) followed by high precision (cross-encoder reranking), implementing a two-stage retrieval architecture.

## Requirements

### Functional Requirements
- FR-1: Accept a user query string (1-2000 characters) and return a ranked list of the top 10 most relevant chunks.
- FR-2: Use GPT-4o-mini to generate 3 semantically diverse query variants from the original query. The original query is also retained, yielding 4 total queries.
- FR-3: Embed all 4 queries using OpenAI `text-embedding-3-small` (same model as ingestion) to produce 4 query vectors of 1536 dimensions.
- FR-4: Execute 4 parallel cosine similarity searches against the pgvector HNSW index, each retrieving the top 20 chunks.
- FR-5: Merge and deduplicate results from all 4 searches by `(document_id, chunk_index)` composite key.
- FR-6: Apply Reciprocal Rank Fusion (RRF) with k=60 to compute fused scores from rank positions across all 4 result sets.
- FR-7: Select the top 30 candidates by RRF score for cross-encoder reranking.
- FR-8: Re-score the top 30 candidates using `cross-encoder/ms-marco-MiniLM-L-6-v2` with the **original user query** (not rewritten variants).
- FR-9: Select the top 10 chunks by cross-encoder confidence score.
- FR-10: Return chunks with metadata: content, document_id, document title, page_number, section_header, chunk_index, cross-encoder score.
- FR-11: Apply relevance threshold: if no chunk has cross-encoder confidence > 0.5, return an empty result set with an `insufficient_context` flag.

### Non-Functional Requirements
- NFR-1: End-to-end retrieval latency (query rewrite + embed + search + RRF + rerank) must be < 4 seconds.
- NFR-2: Query rewriting must complete in < 1.5 seconds.
- NFR-3: 4 parallel vector searches must complete in < 500ms total (concurrent execution).
- NFR-4: Cross-encoder reranking of 30 candidates must complete in < 1.5 seconds on CPU (sequential inference, ~50ms per pair).
- NFR-5: RRF computation must complete in < 50ms.
- NFR-6: System must support 10+ concurrent retrieval requests.
- NFR-7: If query rewriting fails, gracefully degrade to original query only (single search, no RRF).
- NFR-8: If cross-encoder reranking fails, gracefully degrade to RRF-only ranking.

## Constraints
- **Embedding model**: Must use `text-embedding-3-small` for query embeddings — same model as chunk embeddings. Mismatched models produce incomparable vector spaces.
- **Cross-encoder**: Runs on CPU in-process via `sentence-transformers`. No GPU. Model loaded at application startup.
- **Parallelism**: Vector searches run concurrently via `asyncio.gather()`. Cross-encoder is CPU-bound and runs in a thread pool executor.
- **Scope boundary**: This spec produces a ranked chunk list. Context construction and LLM synthesis are handled by spec 004.

## Failure Cases
- **Query rewriting fails** (OpenAI API error): Degrade to single original query. Log warning. Proceed with 1 search instead of 4.
- **Query embedding fails** (OpenAI API error): Return `503 Service Unavailable` with error `"Embedding service temporarily unavailable"`. No fallback.
- **Vector search fails** (pgvector error): Return `503 Service Unavailable` with error `"Vector search temporarily unavailable"`.
- **Cross-encoder fails** (model error, timeout): Degrade to RRF-only ranking. Return top 10 by RRF score. Log warning. Include `"reranking_skipped": true` in response metadata.
- **Cross-encoder timeout** (> 2 seconds): Cancel reranking, use RRF-only. Log warning.
- **All chunks below relevance threshold**: Return empty result set with `"insufficient_context": true` flag. No error — this is a valid outcome.
- **No documents in system**: Return empty result set with `"insufficient_context": true` and `"reason": "no_documents_indexed"`.
- **Empty query**: Return `400 Bad Request` with error `"Query must be between 1 and 2000 characters"`.

## Success Criteria
- Multi-query retrieval returns more relevant chunks than single-query retrieval (measured by manual relevance assessment on test queries).
- Cross-encoder reranking improves precision: top 10 after reranking are more relevant than top 10 by cosine similarity alone.
- RRF correctly deduplicates chunks appearing in multiple query results.
- Retrieval pipeline completes in < 4 seconds for typical queries.
- Graceful degradation works: system returns results even when rewriting or reranking fails.
- Relevance threshold (0.5) correctly filters out irrelevant chunks without discarding relevant ones (verified on test set).

## Out of Scope
- Context construction from retrieved chunks (spec 004)
- LLM answer generation (spec 004)
- Hybrid search with BM25 (Phase 2)
- Metadata filtering during retrieval (Phase 2)
- Relevance feedback or learning-to-rank (Phase 3)
- Query classification or intent detection
