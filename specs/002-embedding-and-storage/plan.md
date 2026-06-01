# Embedding and Storage Implementation Plan

## Architecture Overview
Embedding generation is the final stage of the ingestion worker pipeline. After spec 001 creates chunks and persists them with NULL embeddings, the embedding stage:

1. Collects all chunk texts from the current job
2. Encodes them locally using `BAAI/bge-base-en-v1.5` via `sentence-transformers` (batched, up to 32 per batch)
3. Receives 768-dimensional vectors
4. Updates the `chunks.embedding` column via batch UPDATE
5. Updates document status to `ready`

The HNSW index on the embedding column enables efficient approximate nearest neighbor (ANN) search during query processing (spec 003).

Reference: `/docs/architecture/system-overview.md` — Embedding Worker Components, Database Schema

## Data Flow

### Embedding Generation Flow (within arq worker job)
1. After chunking stage completes, collect all chunk IDs and content texts
2. Pass all chunk texts to the embedding model (batched internally by `sentence-transformers`)
3. Receive 768-dimensional vectors for each chunk
4. Map vectors to chunk IDs by index position
5. Batch UPDATE `chunks` table: set `embedding = vector` WHERE `id = chunk_id`
6. Verify all chunks have non-NULL embeddings
7. Update document status to `ready`

### Local Embedding Call Pattern
```python
from sentence_transformers import SentenceTransformer

# Loaded once at application startup
embedding_model = SentenceTransformer("BAAI/bge-base-en-v1.5")

# For document chunks (no instruction prefix)
embeddings = embedding_model.encode(chunk_texts, batch_size=32, normalize_embeddings=True)
# embeddings[i] is a numpy array of 768 floats
```

## API Design
This spec does not define external API endpoints. Embedding generation is internal to the ingestion worker pipeline.

### Internal Interface
```python
def generate_embeddings(chunk_texts: list[str], is_query: bool = False) -> list[list[float]]:
    """Generate embeddings for a list of texts using local model.
    
    Args:
        chunk_texts: List of text strings to embed
        is_query: If True, prepend query instruction prefix for retrieval
    
    Returns:
        List of 768-dimensional float vectors, same order as input
    
    Raises:
        EmbeddingError: If model inference fails after retries
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
-- chunks.embedding VECTOR(768)

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
| 100 docs | ~5K | ~15 MB | ~23 MB |
| 1,000 docs | ~50K | ~150 MB | ~225 MB |
| 10,000 docs | ~500K | ~1.5 GB | ~2.3 GB |

Formula: 768 dimensions × 4 bytes/float × N chunks = raw storage. HNSW index adds ~50% overhead.

## Pipeline Stages

### Stage 1: Batch Preparation
- **Input**: List of chunk objects (id, content) from chunking stage
- **Processing**: Collect all chunk texts. No manual batching needed — `sentence-transformers` handles batching internally.
- **Output**: List of chunk texts with corresponding chunk IDs
- **Duration**: < 10ms

### Stage 2: Local Model Inference
- **Input**: List of chunk texts
- **Processing**: `embedding_model.encode(texts, batch_size=32, normalize_embeddings=True)` — runs on CPU
- **Output**: List of 768-dimensional vectors (numpy arrays)
- **Duration**: ~3-15 seconds for 50 chunks on CPU (varies by hardware)
- **Retry**: 3 attempts with exponential backoff (1s, 4s, 16s) on failure

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

### Startup Validation
At application startup, after loading the embedding model:
1. Generate a test embedding for a dummy string to verify output dimensionality is 768
2. If the `chunks` table contains any non-NULL embeddings, query one and verify its dimensionality matches 768
3. If either check fails, log a critical error and refuse to start

### Thread Safety
The `SentenceTransformer` model is loaded once at startup and shared across requests. The `model.encode()` method is thread-safe for read-only inference. However, concurrent embedding requests from the ingestion worker and query pipeline should not overlap — the single-worker architecture (ADR-009) ensures sequential access during ingestion. Query-time embedding (spec 003) runs in the API server process, which is separate from the worker.

## Error Handling

| Error | Detection | Response | Retry |
|-------|-----------|----------|-------|
| Model load failure | `OSError`, `RuntimeError` at startup | Application fails to start, log critical | No (fatal) |
| Inference error | `RuntimeError`, `torch` exception | Log, retry batch | Yes (3x backoff) |
| Out of memory | `MemoryError` | Log critical, mark failed | No |
| Token limit exceeded | Input validation | Truncate text, log warning | N/A |
| pgvector write failure | Database exception | Retry batch | Yes (3x backoff) |
| Partial embedding mismatch | Count validation | Retry entire batch | Yes |

**Performance tracking**: Log total chunks embedded per document and inference latency. Format: `{"document_id": "...", "chunks": 47, "embedding_model": "BAAI/bge-base-en-v1.5", "latency_ms": 4500}`.

## Related ADRs
- ADR-001: Use PostgreSQL with pgvector for vector storage
- ADR-014: Migrate to Local Embedding Model (BAAI/bge-base-en-v1.5) (supersedes ADR-004)
- ADR-009: Single worker process for ingestion and embedding
