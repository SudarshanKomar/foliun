# Embedding and Storage Implementation Plan

## Architecture Overview
Embedding generation is the final stage of the ingestion worker pipeline. After spec 001 creates chunks and persists them with NULL embeddings, the embedding stage:

1. Collects all chunk texts from the current job
2. Batches them into OpenAI API requests (up to 2048 per batch)
3. Receives 1536-dimensional vectors
4. Updates the `chunks.embedding` column via batch UPDATE
5. Updates document status to `ready`

The HNSW index on the embedding column enables efficient approximate nearest neighbor (ANN) search during query processing (spec 003).

Reference: `/docs/architecture/system-overview.md` — Embedding Worker Components, Database Schema

## Data Flow

### Embedding Generation Flow (within arq worker job)
1. After chunking stage completes, collect all chunk IDs and content texts
2. Split chunks into batches of ≤ 2048 texts
3. For each batch:
   a. Call OpenAI `embeddings.create()` with model `text-embedding-3-small`
   b. Receive list of 1536-dimensional vectors
   c. Map vectors to chunk IDs by index position
4. Batch UPDATE `chunks` table: set `embedding = vector` WHERE `id = chunk_id`
5. Verify all chunks have non-NULL embeddings
6. Update document status to `ready`

### OpenAI API Call Pattern
```python
response = await openai_client.embeddings.create(
    model="text-embedding-3-small",
    input=chunk_texts,  # list of up to 2048 strings
    encoding_format="float"
)
# response.data[i].embedding is a list of 1536 floats
```

## API Design
This spec does not define external API endpoints. Embedding generation is internal to the ingestion worker pipeline.

### Internal Interface
```python
async def generate_embeddings(chunk_texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of chunk texts.
    
    Args:
        chunk_texts: List of text strings to embed (max 2048 per batch)
    
    Returns:
        List of 1536-dimensional float vectors, same order as input
    
    Raises:
        EmbeddingError: If OpenAI API call fails after retries
    """
```

```python
async def store_embeddings(chunk_ids: list[UUID], embeddings: list[list[float]]) -> None:
    """Store embeddings in pgvector via batch UPDATE.
    
    Args:
        chunk_ids: List of chunk UUIDs
        embeddings: Corresponding embedding vectors
    
    Raises:
        StorageError: If database update fails
    """
```

## Storage Design

### pgvector Configuration
```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Embedding column (already created in spec 001 migration)
-- chunks.embedding VECTOR(1536)

-- HNSW index for cosine similarity search
CREATE INDEX idx_chunks_embedding_hnsw ON chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

### HNSW Index Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `m` | 16 | Number of bi-directional links per node. Default is 16. Balances recall vs build time. |
| `ef_construction` | 64 | Size of dynamic candidate list during index build. Higher = better recall, slower build. 64 is pgvector default. |
| `ef_search` | 40 | Query-time candidate list size. Set via `SET hnsw.ef_search = 40` per session. Higher = better recall, slower query. |
| Distance metric | Cosine (`vector_cosine_ops`) | Matches embedding model's similarity metric. |

### Index Build Strategy
- For initial deployment: create HNSW index after bulk data load
- For incremental inserts: HNSW index updates automatically (slower than bulk build)
- For large re-indexing: use `CREATE INDEX CONCURRENTLY` to avoid table locks

### Storage Estimates
| Scale | Chunks | Embedding Storage | Total Index Size |
|-------|--------|------------------|-----------------|
| 100 docs | ~5K | ~30 MB | ~45 MB |
| 1,000 docs | ~50K | ~300 MB | ~450 MB |
| 10,000 docs | ~500K | ~3 GB | ~4.5 GB |

Formula: 1536 dimensions × 4 bytes/float × N chunks = raw storage. HNSW index adds ~50% overhead.

## Pipeline Stages

### Stage 1: Batch Preparation
- **Input**: List of chunk objects (id, content) from chunking stage
- **Processing**: Split into batches of ≤ 2048 texts. Calculate total token count for cost logging.
- **Output**: List of text batches with corresponding chunk IDs
- **Duration**: < 10ms

### Stage 2: OpenAI API Call
- **Input**: Batch of text strings (≤ 2048)
- **Processing**: Call `openai.embeddings.create()`, await response
- **Output**: List of 1536-dimensional vectors
- **Duration**: ~2-5 seconds per batch (network + API processing)
- **Retry**: 3 attempts with exponential backoff (1s, 4s, 16s)

### Stage 3: Vector Storage
- **Input**: Chunk IDs + embedding vectors
- **Processing**: Batch UPDATE `chunks` table, setting `embedding` column
- **Output**: All chunks have non-NULL embeddings
- **Duration**: < 1 second for 100 chunks

### Stage 4: Finalization
- **Input**: Document ID
- **Processing**: Verify all chunks have embeddings, update document status to `ready`
- **Output**: Document marked as searchable
- **Duration**: < 100ms

## Error Handling

| Error | Detection | Response | Retry |
|-------|-----------|----------|-------|
| OpenAI timeout | `httpx.TimeoutException` | Log, retry batch | Yes (3x backoff) |
| OpenAI rate limit (429) | HTTP 429 response | Wait `Retry-After` seconds, retry | Yes |
| OpenAI server error (5xx) | HTTP 5xx response | Log, retry | Yes (3x backoff) |
| OpenAI auth error (401) | HTTP 401 response | Mark failed, log critical | No |
| Token limit exceeded | Input validation | Truncate text, log warning | N/A |
| pgvector write failure | Database exception | Retry batch | Yes (3x backoff) |
| Partial embedding mismatch | Count validation | Retry entire batch | Yes |

**Cost tracking**: Log total tokens embedded per document for cost monitoring. Format: `{"document_id": "...", "chunks": 47, "total_tokens": 24000, "estimated_cost_usd": 0.00048}`.

## Related ADRs
- ADR-001: Use PostgreSQL with pgvector for vector storage
- ADR-004: Use OpenAI text-embedding-3-small for embeddings
- ADR-009: Single worker process for ingestion and embedding
