# Retrieval Pipeline Implementation Plan

## Architecture Overview
The retrieval pipeline runs synchronously within the FastAPI request handler for `POST /api/v1/query`. It is orchestrated by the Query Orchestrator component, which coordinates 5 sequential stages:

1. **Query Rewriting** (LLM call) → 4 query variants
2. **Query Embedding** (OpenAI API) → 4 query vectors
3. **Parallel Vector Search** (pgvector) → ~80 candidate chunks
4. **Score Fusion** (RRF algorithm) → ranked candidate list
5. **Cross-Encoder Reranking** (in-process model) → top 10 chunks

The output of this pipeline (ranked chunks with metadata) is passed to spec 004 for context construction and LLM synthesis.

Reference: `/docs/architecture/system-overview.md` — Query Pipeline Components, Query/Retrieval Flow

## Data Flow

### Stage 1: Query Rewriting
1. Receive original user query string
2. Send to GPT-4o-mini with system prompt:
   ```
   Generate 3 semantically diverse search queries based on the user's question.
   Each query should approach the topic from a different angle to maximize retrieval coverage.
   Return ONLY the 3 queries, one per line, with no numbering or prefixes.
   ```
3. Parse response into 3 query variant strings
4. Combine with original query → 4 total queries
5. On failure: use original query only (1 query)

### Stage 2: Query Embedding
1. Collect all 4 query strings
2. Single API call: `openai.embeddings.create(model="text-embedding-3-small", input=queries)`
3. Receive 4 vectors of 1536 dimensions
4. Map vectors to queries by index position

### Stage 3: Parallel Vector Search
1. For each of 4 query vectors, execute concurrent pgvector search:
   ```sql
   SELECT c.id, c.document_id, c.chunk_index, c.content, c.token_count,
          c.page_number, c.section_header, c.char_start, c.char_end,
          d.filename,
          1 - (c.embedding <=> query_vector::vector) AS cosine_similarity
   FROM chunks c
   JOIN documents d ON c.document_id = d.id
   WHERE d.status = 'ready'
     AND c.embedding IS NOT NULL
   ORDER BY c.embedding <=> query_vector::vector
   LIMIT 20;
   ```
2. Execute all 4 queries concurrently via `asyncio.gather()`
3. Collect 4 result sets (up to 80 chunks total)

### Stage 4: Reciprocal Rank Fusion (RRF)
1. Assign rank positions (1-indexed) within each result set
2. For each unique chunk (by `(document_id, chunk_index)`):
   - Compute `rrf_score = Σ 1 / (k + rank)` across all result sets where the chunk appears
   - k = 60 (smoothing constant)
3. Sort all chunks by `rrf_score` descending
4. Select top 30 candidates for reranking

### Stage 5: Cross-Encoder Reranking
1. Load `cross-encoder/ms-marco-MiniLM-L-6-v2` model (loaded once at startup)
2. Prepare (original_query, chunk_content) pairs for top 30 candidates
3. Run cross-encoder inference in thread pool executor (CPU-bound)
4. Receive confidence scores [0, 1] for each pair
5. Sort by cross-encoder score descending
6. Select top 10 chunks
7. Check relevance threshold: if max score < 0.5 → insufficient context

### Output Structure
```python
@dataclass
class RetrievalResult:
    chunks: list[RankedChunk]       # Top 10 (or fewer) ranked chunks
    insufficient_context: bool       # True if all scores < 0.5
    metadata: RetrievalMetadata      # Pipeline diagnostics

@dataclass
class RankedChunk:
    chunk_id: UUID
    document_id: UUID
    document_title: str              # filename without extension
    content: str
    page_number: int | None
    section_header: str | None
    chunk_index: int
    cross_encoder_score: float       # 0.0 - 1.0
    rrf_score: float                 # For debugging

@dataclass
class RetrievalMetadata:
    original_query: str
    rewritten_queries: list[str]
    total_candidates: int            # Before deduplication
    unique_candidates: int           # After deduplication
    reranking_applied: bool
    reranking_skipped_reason: str | None
    stage_latencies: dict[str, float]  # e.g., {"rewrite": 0.8, "embed": 0.3, ...}
```

## API Design
The retrieval pipeline is internal to the query endpoint. The external API is `POST /api/v1/query` defined in spec 005. This spec defines the internal pipeline interface.

### Internal Pipeline Interface
```python
async def execute_retrieval(
    query: str,
    db: AsyncSession,
    openai_client: AsyncOpenAI,
    cross_encoder: CrossEncoder,
) -> RetrievalResult:
    """Execute the full retrieval pipeline.
    
    Stages: rewrite → embed → search → RRF → rerank
    Graceful degradation on rewrite or rerank failure.
    """
```

## Storage Design
This spec reads from the database only — no writes. Schema is defined in specs 001 and 002.

### Query Patterns
- **Vector search**: `SELECT ... ORDER BY embedding <=> query_vector LIMIT 20` — uses HNSW index
- **Document join**: `JOIN documents ON chunks.document_id = documents.id WHERE documents.status = 'ready'` — filters to searchable documents only

### Session Configuration
```sql
-- Set at connection/session level for optimal HNSW recall
SET hnsw.ef_search = 40;
```

## Pipeline Stages (Summary)

| Stage | Input | Output | Duration Target | Fallback |
|-------|-------|--------|----------------|----------|
| 1. Query Rewrite | User query (str) | 4 query strings | < 1.5s | Original only |
| 2. Query Embed | 4 query strings | 4 × VECTOR(1536) | < 500ms | None (fatal) |
| 3. Vector Search | 4 query vectors | ~80 chunks | < 500ms | None (fatal) |
| 4. RRF Fusion | ~80 chunks | 30 ranked chunks | < 50ms | None |
| 5. Rerank | 30 chunks + query | 10 ranked chunks | < 500ms | Use RRF top 10 |

**Total target**: < 4 seconds (excluding context construction and LLM synthesis)

## Error Handling

| Error | Detection | Response | Logging |
|-------|-----------|----------|---------|
| Query rewrite timeout | `asyncio.TimeoutError` after 3s | Use original query only | WARN with latency |
| Query rewrite LLM error | OpenAI API exception | Use original query only | WARN with error |
| Query rewrite bad output | Parsing failure (< 3 lines) | Use whatever parsed + original | WARN with raw response |
| Embedding API failure | OpenAI exception | 503 to client | ERROR with details |
| Vector search failure | Database exception | 503 to client | ERROR with query |
| RRF produces 0 results | Empty candidate set | Return insufficient_context | INFO |
| Reranker model failure | `sentence-transformers` exception | Use RRF-only ranking | WARN with error |
| Reranker timeout | Thread pool timeout (2s) | Use RRF-only ranking | WARN with latency |
| All scores below threshold | Max score < 0.5 | Return insufficient_context=true | INFO with scores |

## Related ADRs
- ADR-004: Use OpenAI text-embedding-3-small for embeddings
- ADR-005: Use Reciprocal Rank Fusion for multi-query score merging
- ADR-006: Use cross-encoder ms-marco-MiniLM-L-6-v2 for reranking
- ADR-011: Use GPT-4o-mini as primary LLM
- ADR-012: Remove general knowledge fallback
