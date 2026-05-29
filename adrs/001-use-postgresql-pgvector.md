# ADR-001: Use PostgreSQL with pgvector for Vector Storage

## Status
Accepted

## Context
The AI Research Workspace requires both relational data storage (documents, chunks, metadata, ingestion state) and vector similarity search (embedding-based retrieval). The key decision is whether to use a dedicated vector database (Qdrant, Weaviate, Pinecone) alongside PostgreSQL, or to use PostgreSQL's pgvector extension to handle both workloads in a single database.

Phase 1 targets 1,000+ documents and 100K+ chunks. The team is small, and operational simplicity is a priority. The system must support HNSW-based approximate nearest neighbor (ANN) search with cosine distance.

## Decision
We will use **PostgreSQL 16 with pgvector 0.7+** as the single database for both relational data and vector similarity search.

- Vector embeddings stored in `VECTOR(1536)` columns
- HNSW index with parameters: `m=16`, `ef_construction=64`, cosine distance operator
- All relational data (documents, chunks, metadata, status) co-located in the same database
- No dedicated vector database in Phase 1

## Consequences

### Positive
- Single database to operate, back up, and monitor — significantly reduced operational complexity
- Native SQL joins between relational data and vector search results (e.g., filter by document status)
- ACID transactions for consistent state management during ingestion
- No additional infrastructure to deploy or maintain
- pgvector HNSW provides ~5-20ms query latency at 100K vectors, sufficient for Phase 1

### Negative
- pgvector performance degrades beyond ~1M vectors; may require migration to a dedicated vector DB
- HNSW index build time increases with dataset size; must use `CREATE INDEX CONCURRENTLY` for large datasets
- No built-in vector-specific features like automatic sharding or multi-tenancy
- Limited to single-node performance (no distributed vector search)

### Neutral
- pgvector is a well-maintained, actively developed extension with strong community adoption
- Migration path to a dedicated vector DB exists but requires code changes to the retrieval layer

## Related ADRs
- ADR-003: Use Redis with arq for job queue management
- ADR-005: Use Reciprocal Rank Fusion for multi-query score merging
