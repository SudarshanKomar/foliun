# Context Construction and LLM Synthesis Implementation Tasks

## Phase 1: Foundation
- [ ] Create data classes: ContextResult, SourceInfo, SSEEvent (estimate: 1h)
- [ ] Set up OpenAI async client for chat completions with streaming (estimate: 1h)
- [ ] Set up Ollama client using OpenAI-compatible API at localhost:11434 (estimate: 1h)
- [ ] Create system prompt template as a configurable constant (estimate: 0.5h)
- [ ] Set up tiktoken cl100k_base encoder for token counting (estimate: 0.5h)

## Phase 2: Core Implementation
- [ ] Implement context constructor: sort chunks by position, format with source headers, enforce token budget (estimate: 3h)
- [ ] Implement token budget calculation: system prompt + context + query overhead accounting (estimate: 1.5h)
- [ ] Implement prompt assembler: combine system prompt + delimited context + user query into messages array (estimate: 1h)
- [ ] Implement GPT-4o-mini streaming synthesis: async generator yielding SSE events from OpenAI streaming response (estimate: 3h)
- [ ] Implement Ollama Gemma 4 2B streaming synthesis: async generator yielding SSE events from Ollama /v1/chat/completions endpoint (estimate: 2h)
- [ ] Implement model selection logic: route to GPT-4o-mini or Gemma 4 based on user preference (estimate: 1h)
- [ ] Implement Ollama fallback: detect Ollama unavailability (connection refused at localhost:11434), switch to GPT-4o-mini, emit notification event (estimate: 1.5h)
- [ ] Implement SSE event formatting: token, citation, done, error event types with JSON payloads (estimate: 1.5h)
- [ ] Implement FastAPI StreamingResponse endpoint with async generator (estimate: 2h)
- [ ] Implement insufficient context response: return structured JSON when no relevant chunks found (estimate: 1h)
- [ ] Implement citation extraction: regex parse [Doc: title, Page: N] from accumulated response (estimate: 1.5h)
- [ ] Implement citation validation: check extracted citations against source list, log warnings (estimate: 1h)
- [ ] Implement client disconnect detection: cancel LLM call on ConnectionResetError (estimate: 1h)
- [ ] Implement connection timeout: 120-second SSE connection limit (estimate: 0.5h)

## Phase 3: Testing & Refinement
- [ ] Unit test: context constructor — ordering, token budget enforcement, source header formatting (estimate: 2h)
- [ ] Unit test: token counting — verify counts match tiktoken for various chunk sizes (estimate: 1h)
- [ ] Unit test: citation extraction regex — valid citations, malformed citations, no citations (estimate: 1h)
- [ ] Unit test: citation validation — valid sources, invalid sources, mixed (estimate: 1h)
- [ ] Unit test: insufficient context path — verify no LLM call, correct JSON response (estimate: 1h)
- [ ] Integration test: full query → retrieval → context → synthesis → SSE stream with real LLM (estimate: 3h)
- [ ] Integration test: Ollama fallback — simulate Ollama unavailability, verify GPT-4o-mini fallback (estimate: 2h)
- [ ] Integration test: SSE event format — verify token, done, error events parse correctly (estimate: 1.5h)
- [ ] Integration test: client disconnect handling — verify clean cleanup (estimate: 1h)
- [ ] Performance test: first token latency < 3 seconds from query submission (estimate: 1h)
- [ ] Manual test: verify LLM respects grounding constraints on 10 test queries (estimate: 2h)

## Phase 4: Documentation & Cleanup
- [ ] Document system prompt and grounding instructions (estimate: 0.5h)
- [ ] Document SSE event format with examples for API consumers (estimate: 1h)
- [ ] Document Ollama setup: installation, model pull (gemma-4-2b), configuration, and health check (estimate: 1h)
- [ ] Document citation format specification (estimate: 0.5h)
