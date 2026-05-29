# ADR-004: Use OpenAI text-embedding-3-small for Embeddings

## Status
Accepted

## Context
The system requires a text embedding model to convert document chunks and user queries into vector representations for semantic similarity search. The model must produce high-quality embeddings for English text, support inputs up to 512 tokens (our chunk size), and be cost-effective for both ingestion and query workloads.

Candidates considered: OpenAI `text-embedding-3-small`, OpenAI `text-embedding-3-large`, open-source models via `sentence-transformers` (e.g., `all-MiniLM-L6-v2`, `bge-base-en-v1.5`), Cohere Embed.

## Decision
We will use **OpenAI `text-embedding-3-small`** for all embedding generation.

- Output dimensionality: **1536 dimensions** (default, no reduction applied)
- Maximum input: 8191 tokens per text
- Cost: $0.02 per 1M tokens
- Batch API: up to 2048 texts per request
- **Critical constraint**: The same model must be used for both chunk embeddings (ingestion) and query embeddings (retrieval). Mismatched models produce incomparable vector spaces.

## Consequences

### Positive
- High embedding quality with strong benchmark performance (MTEB)
- Simple integration via OpenAI Python SDK (`openai.embeddings.create()`)
- Batch API significantly reduces latency for ingestion (2048 texts/request)
- Cost-effective: a 10-page PDF (~50 chunks) costs ~$0.0005 to embed
- No GPU infrastructure required; runs via API

### Negative
- Hard dependency on OpenAI API — no offline/air-gapped operation
- Network latency added to every embedding operation (~100-300ms per batch)
- 1536 dimensions is relatively large; increases pgvector storage and index size
- OpenAI API rate limits may throttle burst ingestion (can be mitigated with backoff)
- Vendor lock-in: switching models requires re-embedding all existing chunks

### Neutral
- `text-embedding-3-small` supports dimensionality reduction (e.g., to 512d) via API parameter, but we use full 1536d for maximum quality in Phase 1
- Migration to open-source embeddings (e.g., via `sentence-transformers`) is possible but requires full re-indexing

## Related ADRs
- ADR-001: Use PostgreSQL with pgvector for vector storage
- ADR-007: Use recursive character text splitting for chunking
