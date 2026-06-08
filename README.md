# Foliun

An AI Research Workspace with RAG (Retrieval-Augmented Generation) capabilities for intelligent document analysis and query.

## Overview

Foliun is a spec-driven RAG system that enables users to upload research documents and ask natural language questions about their content. The system retrieves relevant document chunks, synthesizes answers using LLMs, and provides citations back to source material.

## Tech Stack

- **Backend**: FastAPI (Python 3.14)
- **Database**: PostgreSQL 18 + pgvector 0.8.1
- **Job Queue**: Redis + arq
- **Embeddings**: `BAAI/bge-base-en-v1.5` (768 dimensions) via `sentence-transformers` — local-only, free, CPU-friendly
- **LLM**: Gemma 4 2B via Ollama (default, local), GPT-4o-mini (optional opt-in)
- **Reranking**: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Streaming**: Server-Sent Events (SSE)

## Features

- **Document Ingestion**: Upload PDF documents with automatic text extraction
- **Intelligent Retrieval**: Multi-query search with RRF fusion and cross-encoder reranking
- **Context-Aware Answers**: Token-budgeted responses with source citations
- **Streaming Responses**: Real-time answer generation via SSE
- **Local-First Architecture**: All default operations run offline — local embeddings and Gemma 4 2B via Ollama. GPT-4o-mini available as opt-in alternative.
- **API Key Authentication**: Secure access control

## Documentation

This project follows a spec-driven development approach with comprehensive documentation:

- **[System Overview](docs/architecture/system-overview.md)** - Architecture, C4 diagrams, data flows, and non-functional requirements
- **[Architecture Decision Records (ADRs)](adrs/)** - Technical decisions and rationale
- **[Specifications](specs/)** - Detailed specs for each system component
- **[Consistency Verification Report](docs/review-report/consistency-verification-report.md)** - Cross-document verification results

## Phase 1 Scope

- PDF document ingestion (text extraction, chunking, embedding)
- Multi-query retrieval with RRF fusion
- Cross-encoder reranking
- Context construction with citations
- Streaming query responses
- API key authentication
- Observability (logging, metrics)
- Local-first LLM (Gemma 4 2B via Ollama, default) with optional GPT-4o-mini

## Getting Started

See the [Document Ingestion Spec](specs/001-document-ingestion/spec.md) for detailed implementation guidance.

## Development

This project uses spec-driven development. All implementation decisions are documented in ADRs and specifications before code is written.

## License

MIT
