# Context Construction and LLM Synthesis Specification

## Context
After the retrieval pipeline (spec 003) produces a ranked list of relevant chunks, the system must construct a well-structured context window and use an LLM to generate a grounded, cited answer. This is the final stage of the query pipeline — where retrieved information is transformed into a useful response.

Context construction is critical: chunks must be ordered for coherent reading, fit within a token budget, and include metadata for citation generation. The LLM must be constrained to only use the provided context (grounding) and produce citations in a consistent format. Responses must stream to the client in real-time via Server-Sent Events.

This spec covers context assembly, system prompt design, LLM synthesis, citation handling, SSE streaming, and the insufficient context path.

## Requirements

### Functional Requirements
- FR-1: Construct context from top chunks (up to 10) within a ~4000 token budget. Chunks that would exceed the budget are excluded.
- FR-2: Order chunks by document source position (document_id, then chunk_index) for coherent reading — not by relevance score.
- FR-3: Format each chunk in the context with source metadata: `[Source: {document_title}, Page: {page_number}]` header followed by chunk content.
- FR-4: Prepend a grounding system prompt that instructs the LLM to answer using ONLY the provided context and cite sources using `[Doc: title, Page: N]` format.
- FR-5: Support model selection: GPT-4o-mini (default) or Gemma 4 2B via Ollama (localhost:11434). Model specified by user in query request.
- FR-6: Stream LLM response to client via Server-Sent Events (SSE) using `text/event-stream` content type.
- FR-7: If retrieval returns `insufficient_context=true`, return a structured message indicating no relevant documents were found. No LLM call is made.
- FR-8: Validate citations in the generated response: warn (via logs) if the LLM cites a source not present in the provided context.
- FR-9: Include SSE event types: `token` (content chunk), `citation` (structured citation metadata), `done` (completion signal), `error` (failure notification).
- FR-10: Include retrieval metadata in the `done` event: number of sources used, total chunks considered, pipeline latency.

### Non-Functional Requirements
- NFR-1: First token must arrive within 5 seconds of query submission (including retrieval pipeline time).
- NFR-2: SSE connection timeout: 120 seconds (accommodates slow LLM responses for complex queries).
- NFR-3: Context construction must complete in < 100ms.
- NFR-4: System must support 10+ concurrent streaming responses.
- NFR-5: If Ollama is unavailable, fall back to GPT-4o-mini with a notification in the response.

## Constraints
- **Grounding**: The LLM must NEVER generate answers from its own knowledge. Only content from the provided context is allowed.
- **Citation format**: Strict format `[Doc: {title}, Page: {N}]` — consistent across all responses.
- **Token budget**: ~4000 tokens for context. System prompt + context + user query must fit within model input limits.
- **No general knowledge**: If no relevant chunks exist, return "insufficient context" — do not fall back to ungrounded LLM response (per ADR-012).
- **Streaming protocol**: SSE only. No WebSocket. No long-polling.

## Failure Cases
- **LLM API timeout** (GPT-4o-mini): Send SSE `error` event with `"LLM response timed out"`. Close stream.
- **LLM API error** (5xx): Send SSE `error` event with `"LLM service temporarily unavailable"`. Close stream.
- **Ollama unavailable**: Fall back to GPT-4o-mini. Include `"model_fallback": "gpt-4o-mini"` in response metadata.
- **Context exceeds token limit**: Truncate context by removing lowest-scored chunks until within budget. Log warning.
- **Citation validation failure**: Log warning with uncited source details. Do not interrupt response — citation issues are non-fatal.
- **Client disconnects mid-stream**: Detect disconnection, cancel LLM generation, clean up resources. No error to client.
- **Empty context** (insufficient context): Return structured JSON message, no SSE stream: `{"insufficient_context": true, "message": "No relevant documents found for your query."}`.

## Success Criteria
- Context correctly orders chunks by document position (verified on multi-document queries).
- Token budget is respected: constructed context is ≤ 4000 tokens.
- LLM generates answers that are grounded in provided context (manual verification on test set).
- Citations in responses reference actual source documents provided in context.
- SSE stream delivers tokens in real-time with < 100ms inter-token latency.
- First streamed token arrives within 5 seconds of query submission.
- Insufficient context queries return the structured message without an LLM call.
- Ollama fallback to GPT-4o-mini works transparently.

## Out of Scope
- Chat history / multi-turn conversation (single query-response only)
- Response caching
- Answer post-processing beyond citation validation
- User feedback on answer quality (Phase 3)
- Response summarization or length control
