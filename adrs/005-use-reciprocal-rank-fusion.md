# ADR-005: Use Reciprocal Rank Fusion for Multi-Query Score Merging

## Status
Accepted

## Context
The retrieval pipeline generates 4 query variants (original + 3 LLM-generated rewrites) and executes parallel vector searches for each. The results from these 4 searches must be merged into a single ranked list before reranking. The merging strategy must handle:

- Duplicate chunks appearing in multiple result sets
- Different score distributions across queries (cosine similarity scores are not directly comparable across different query embeddings)
- Fair treatment of all query variants

Candidates considered: Max score fusion, average score fusion, Reciprocal Rank Fusion (RRF), Combsum/Combmnz.

## Decision
We will use **Reciprocal Rank Fusion (RRF)** with **k=60** to merge results from multiple query variants.

RRF formula: `RRF_score(d) = Σ 1 / (k + rank_i(d))` where `rank_i(d)` is the rank of document `d` in result set `i` and `k=60` is a smoothing constant.

- Deduplication by `(document_id, chunk_index)` composite key
- Chunks appearing in multiple result sets get accumulated RRF scores
- Output: single ranked list sorted by RRF score descending
- Top 30 candidates passed to cross-encoder reranking

## Consequences

### Positive
- Rank-based fusion is robust to different score distributions across queries
- No score normalization required — works directly on rank positions
- Industry standard: used in Elasticsearch, Vespa, and academic RAG systems
- Simple implementation (~20 lines of code)
- k=60 is the standard smoothing constant from the original paper (Cormack et al., 2009)

### Negative
- Loses absolute score information — a chunk ranked #1 with high confidence and one ranked #1 with low confidence get the same RRF contribution
- Requires all result sets to be retrieved before fusion (cannot stream results)
- k=60 is not optimized for this specific use case (may benefit from tuning in Phase 2)

### Neutral
- RRF is purely a ranking fusion mechanism; the cross-encoder reranking step corrects for any RRF ranking errors
- The choice of k=60 follows the original paper's recommendation and is widely used

## Related ADRs
- ADR-006: Use cross-encoder ms-marco-MiniLM-L-6-v2 for reranking
- ADR-004: Use OpenAI text-embedding-3-small for embeddings
