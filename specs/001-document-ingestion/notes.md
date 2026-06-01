# Document Ingestion Notes

## Research Links
- [PyMuPDF documentation](https://pymupdf.readthedocs.io/) — PDF text extraction, page iteration
- [transformers AutoTokenizer](https://huggingface.co/docs/transformers/main_classes/tokenizer) — BERT WordPiece tokenizer from `BAAI/bge-base-en-v1.5` for token counting
- [LangChain RecursiveCharacterTextSplitter](https://python.langchain.com/docs/modules/data_connection/document_transformers/recursive_text_splitter) — Reference implementation for recursive splitting
- [arq documentation](https://arq-docs.helpmanual.io/) — Async job queue with retry support
- [FastAPI UploadFile](https://fastapi.tiangolo.com/tutorial/request-files/) — Multipart file upload handling

## Design Discussions

### Recursive vs Naive Fixed-Size Chunking
Naive fixed-size splits text at exact character/token boundaries, frequently cutting mid-sentence. Recursive character splitting attempts to split at natural boundaries (paragraphs → lines → sentences → words) before falling back to character splits. This produces more semantically coherent chunks with minimal implementation complexity over naive splitting.

We chose NOT to use LangChain's implementation directly to avoid the large dependency. Instead, implement the same algorithm (~50 lines) with the BERT WordPiece tokenizer from `BAAI/bge-base-en-v1.5` (via `transformers.AutoTokenizer`) for token counting, ensuring exact alignment with the embedding model's tokenization.

### Page Number Attribution
For PDFs, we maintain a mapping of `page_index → (char_start, char_end)` by tracking the cumulative character offset as we iterate pages. Each chunk's `char_start` is then binary-searched against this mapping to determine the page number. Chunks that span page boundaries are attributed to the page where they start.

### Section Header Detection
A simple heuristic approach: lines that are (a) ≤ 100 characters, (b) followed by a blank line or start of paragraph, and (c) don't end with a period are treated as potential section headers. The most recent detected header before a chunk's start position becomes that chunk's `section_header`. This is imperfect but sufficient for Phase 1.

### Embedding Column Strategy
The `chunks` table includes an `embedding VECTOR(768)` column that is created as nullable (768d for `BAAI/bge-base-en-v1.5`, local-only). This spec creates chunks with NULL embeddings. Spec 002-embedding-and-storage is responsible for populating embeddings and creating the HNSW index. This separation allows the ingestion pipeline to complete even if the embedding model encounters a transient error.

### Duplicate Detection Approach
We use `(filename, file_hash)` for duplicate detection rather than file hash alone. This allows users to upload different files with the same name (different content) or the same file with a different name (different use case). Only exact filename + content matches are treated as duplicates.

## Lessons Learned
*(To be filled during implementation)*

## Open Questions
- Should we support re-processing a failed document via API (e.g., `POST /api/v1/documents/{id}/retry`)?
- Should chunk overlap be configurable per document or globally only?
- How to handle PDFs with unusual encodings (CJK fonts, ligatures)?
- Should we store the raw extracted text in the `documents` table for debugging purposes?
