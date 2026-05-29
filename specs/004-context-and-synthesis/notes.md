# Context Construction and LLM Synthesis Notes

## Research Links
- [OpenAI Chat Completions Streaming](https://platform.openai.com/docs/api-reference/chat/create#chat-create-stream) — Streaming API reference
- [FastAPI StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse) — SSE implementation in FastAPI
- [Ollama API Documentation](https://github.com/ollama/ollama/blob/main/docs/api.md) — Ollama REST API and OpenAI compatibility
- [SSE Specification](https://html.spec.whatwg.org/multipage/server-sent-events.html) — W3C EventSource spec
- [tiktoken](https://github.com/openai/tiktoken) — Token counting for context budget management

## Design Discussions

### Chunk Ordering: By Score vs By Position
Two options for ordering chunks in the context window:
1. **By relevance score** (highest first): LLM sees the most relevant chunk first, which may improve answer quality for simple questions.
2. **By document position** (document_id, chunk_index): Preserves narrative flow. Adjacent chunks from the same document are read in order, preserving context.

We chose **position-based ordering** because:
- Research papers and technical documents have logical flow — preserving it improves synthesis quality
- Multiple adjacent chunks from the same document should be read sequentially
- The LLM can synthesize across the full context regardless of order
- Score-based ordering fragments the narrative and makes citation harder

### Token Budget: 4000 Tokens
GPT-4o-mini has a 128K context window — we could theoretically provide much more context. However:
- More context increases response latency (more tokens to process)
- Diminishing returns: beyond ~10 chunks, additional context rarely improves answers
- Cost scales linearly with input tokens
- 4000 tokens ≈ 10 chunks × 400 tokens average (accounting for overlap and metadata headers)

The budget includes chunk content + source headers. System prompt (~100 tokens) and user query (~50 tokens) are budgeted separately.

### System Prompt Design
The grounding prompt is intentionally strict: "Answer using ONLY the provided context." This minimizes hallucination but may make the LLM refuse to answer when relevant information is partially present. This is the preferred behavior — false negatives (refusing to answer) are better than false positives (hallucinated answers) for a research tool.

The citation format `[Doc: title, Page: N]` was chosen for readability and parseability. It is human-readable in the response and machine-parseable for validation.

### SSE vs Returning Complete Response
We chose SSE streaming because:
- LLM responses can take 5-30 seconds to generate completely
- Streaming reduces perceived latency — users see tokens within 1-3 seconds
- SSE is simpler than WebSocket for unidirectional streaming
- Native browser support via `EventSource` API

The tradeoff is that error handling mid-stream is harder. If the LLM fails after streaming 50% of the response, the client receives a partial answer followed by an error event.

### Citation Validation Strategy
Citation validation runs post-generation (after the stream completes) by accumulating all tokens and regex-matching citation patterns. This is a best-effort validation — the LLM may cite sources in unexpected formats. Invalid citations are logged as warnings but do not invalidate the response.

In Phase 2, we could add inline citation detection during streaming and emit `citation` events in real-time.

### Ollama Integration Considerations
Ollama runs Gemma 4 2B locally via `localhost:11434`. Key differences from OpenAI:
- OpenAI-compatible API at `/v1/chat/completions` — can reuse same client code with different base URL
- Streaming via chunked HTTP responses (same SSE-compatible format)
- Higher latency than GPT-4o-mini for first token (~2-5s cold start, ~1s warm)
- Less reliable instruction following (2B model has limited capability vs GPT-4o-mini)
- Data stays local — true privacy, no external data transmission
- Ollama must be installed and running separately from the RAG application
- Model must be pre-pulled: `ollama pull gemma3:4b` (or appropriate Gemma 4 2B tag)

The Ollama integration should be abstracted behind the same `synthesize_answer()` interface so that model selection is transparent to the rest of the pipeline. Since Ollama supports the OpenAI-compatible API, the same `openai.AsyncOpenAI` client can be used with a different `base_url` parameter.

## Lessons Learned
*(To be filled during implementation)*

## Open Questions
- Should we implement response length limits (max tokens for LLM output)?
- Should we stream the insufficient context message as SSE, or return it as regular JSON?
- How should we handle multi-language output if the context contains non-English text?
- Should we add a "confidence score" to the response based on cross-encoder scores?
- Should the system prompt be versioned for A/B testing in Phase 2?
