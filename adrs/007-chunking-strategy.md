# ADR-007: Use Recursive Character Text Splitting for Chunking

## Status
Accepted

## Context
Document text must be split into chunks for embedding and retrieval. The chunking strategy directly impacts retrieval quality: too large and chunks contain noise; too small and chunks lose context. Chunks must be predictable in size (for token budget management) and respect natural text boundaries (sentences, paragraphs) to preserve semantic coherence.

Candidates considered: naive fixed-size (character count), fixed-size token-based, recursive character text splitting, semantic chunking (model-based), document-structure-aware splitting.

## Decision
We will use **recursive character text splitting** with the following parameters:

- **Target chunk size**: 512 tokens
- **Overlap**: 20% (102 tokens)
- **Separator hierarchy**: `["\n\n", "\n", ". ", " ", ""]` (paragraphs → lines → sentences → words → characters)
- **Token counting**: `tiktoken` with `cl100k_base` encoding (matches OpenAI models)
- **Metadata per chunk**: document title, section header, page number, chunk index, char_start, char_end

The recursive strategy attempts to split at the highest-level separator first (paragraph breaks), falling back to lower-level separators only when the resulting chunk exceeds the target size.

## Consequences

### Positive
- Respects natural text boundaries (sentences, paragraphs) — better semantic coherence than naive fixed-size
- Predictable chunk sizes for consistent token budget management
- 20% overlap ensures context is preserved across chunk boundaries
- Simple implementation using LangChain's `RecursiveCharacterTextSplitter` or equivalent
- Token-based sizing matches the embedding model's token limit (8191 tokens)

### Negative
- Fixed-size approach doesn't adapt to document structure (e.g., a 512-token chunk may span two unrelated sections)
- 20% overlap increases storage by ~20% (more chunks, more embeddings, higher cost)
- Recursive splitting may still break mid-sentence in dense text with no paragraph breaks
- No semantic awareness — cannot determine optimal split points based on meaning

### Neutral
- 512 tokens is a widely-used default; optimal chunk size is data-dependent and may benefit from tuning in Phase 2
- Semantic chunking (Phase 2) would address the semantic coherence limitation but adds model dependency and complexity
- The separator hierarchy can be adjusted per document type if needed

## Related ADRs
- ADR-004: Use OpenAI text-embedding-3-small for embeddings
- ADR-001: Use PostgreSQL with pgvector for vector storage
