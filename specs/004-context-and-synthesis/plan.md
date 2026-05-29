# Context Construction and LLM Synthesis Implementation Plan

## Architecture Overview
This spec covers the final two stages of the query pipeline, executing synchronously within the `POST /api/v1/query` request handler:

1. **Context Constructor**: Takes ranked chunks from the retrieval pipeline (spec 003), orders them, formats with metadata, and assembles within a token budget.
2. **LLM Synthesizer**: Sends the constructed context + system prompt + user query to the selected LLM, streams the response back via SSE.

Both stages run in the FastAPI server process. LLM calls are async (via `httpx` / OpenAI SDK). SSE streaming uses FastAPI's `StreamingResponse` with an async generator.

Reference: `/docs/architecture/system-overview.md` — Query Pipeline Components, Context Construction, SSE Streaming

## Data Flow

### Context Construction Flow
1. Receive `RetrievalResult` from spec 003 pipeline
2. Check `insufficient_context` flag:
   - If `true`: return structured JSON response immediately (no LLM call)
   - If `false`: proceed to context construction
3. Sort chunks by `(document_id, chunk_index)` for coherent reading order
4. Build context string, iterating chunks:
   - For each chunk, prepend `[Source: {document_title}, Page: {page_number}]\n`
   - Append chunk content + `\n\n`
   - Track cumulative token count (via tiktoken)
   - Stop adding chunks when budget (~4000 tokens) would be exceeded
5. Assemble full prompt:
   - System prompt (grounding instructions)
   - `---CONTEXT START---\n{context}\n---CONTEXT END---`
   - User query

### System Prompt
```
You are a research assistant that answers questions using ONLY the provided document context.

Rules:
1. Answer based ONLY on the information in the context below. Do not use any external knowledge.
2. Cite your sources using the format [Doc: <title>, Page: <N>] after each claim.
3. If the context does not contain enough information to answer the question, say "The provided documents do not contain sufficient information to answer this question."
4. Be concise and accurate.
5. If multiple documents are relevant, synthesize information across sources.
```

### LLM Synthesis Flow
1. Select model based on user preference:
   - `"gpt-4o-mini"` (default): OpenAI API
   - `"gemma-4-2b"`: Ollama local API (localhost:11434)
2. Call LLM with streaming enabled:
   - GPT-4o-mini: `openai.chat.completions.create(stream=True)`
   - Gemma 4 2B: Ollama `/v1/chat/completions` endpoint with streaming output
3. Stream tokens to client via SSE async generator:
   ```
   event: token
   data: {"content": "The research"}

   event: token
   data: {"content": " paper describes"}
   ```
4. On stream completion, emit `done` event with metadata:
   ```
   event: done
   data: {"sources_used": 3, "chunks_in_context": 7, "model": "gpt-4o-mini", "latency_ms": 4200}
   ```

### SSE Event Format
```
event: <event_type>
data: <json_payload>

```

| Event Type | Payload | When |
|------------|---------|------|
| `token` | `{"content": "..."}` | Each LLM output token/chunk |
| `citation` | `{"title": "paper.pdf", "page": 5}` | Detected inline citation |
| `done` | `{"sources_used": N, "chunks_in_context": N, "model": "...", "latency_ms": N}` | Stream complete |
| `error` | `{"error": "...", "detail": "..."}` | Any error during synthesis |

### Insufficient Context Response (No SSE)
```json
{
  "insufficient_context": true,
  "message": "No relevant documents found for your query. Try uploading documents related to your question.",
  "query": "What is the capital of Mars?"
}
```
Returned as regular `200 OK` JSON (not SSE stream).

## API Design
The external API is `POST /api/v1/query` (defined in spec 005). This plan defines the internal context + synthesis interfaces.

### Internal Interfaces
```python
def construct_context(
    chunks: list[RankedChunk],
    max_tokens: int = 4000,
) -> ContextResult:
    """Build context string from ranked chunks within token budget.
    
    Returns:
        ContextResult with context string, included chunk count, 
        total tokens, and list of source documents.
    """

@dataclass
class ContextResult:
    context_text: str
    chunks_included: int
    total_tokens: int
    sources: list[SourceInfo]  # unique documents referenced

@dataclass
class SourceInfo:
    document_id: UUID
    document_title: str
    pages_referenced: list[int]
```

```python
async def synthesize_answer(
    query: str,
    context: ContextResult,
    model: str = "gpt-4o-mini",
) -> AsyncGenerator[SSEEvent, None]:
    """Generate streamed answer from context using selected LLM.
    
    Yields SSE events: token, citation, done, error.
    """
```

## Storage Design
This spec does not write to or read from the database directly. It consumes `RetrievalResult` from spec 003 and produces SSE output to the client.

### Token Counting
- Use `tiktoken` with `cl100k_base` encoding (matches GPT-4o-mini tokenizer)
- Count tokens for: system prompt (~100 tokens) + context + user query
- Reserve ~4000 tokens for context, ~200 for system prompt + query overhead
- Model input limit: 128K tokens (GPT-4o-mini) — well within budget

## Pipeline Stages

### Stage 1: Context Construction
- **Input**: `RetrievalResult` (list of RankedChunk from spec 003)
- **Processing**: Sort by position, format with source headers, accumulate within token budget
- **Output**: `ContextResult` with assembled context string
- **Duration**: < 100ms

### Stage 2: Prompt Assembly
- **Input**: System prompt template, context string, user query
- **Processing**: Concatenate system prompt + delimited context + user query into messages array
- **Output**: LLM messages array
- **Duration**: < 10ms

### Stage 3: LLM Call + SSE Streaming
- **Input**: Messages array, model selection
- **Processing**: Call LLM API with streaming, yield SSE events
- **Output**: SSE event stream
- **Duration**: 1-30 seconds depending on answer length

### Stage 4: Citation Extraction (Background)
- **Input**: Generated response text (accumulated from tokens)
- **Processing**: Regex match `\[Doc: (.+?), Page: (\d+)\]` patterns, validate against source list
- **Output**: Log warnings for invalid citations
- **Duration**: < 10ms (runs after stream completes)

## Error Handling

| Error | Detection | SSE Event | Recovery |
|-------|-----------|-----------|----------|
| LLM API timeout | `asyncio.TimeoutError` (120s) | `error: {"error": "llm_timeout"}` | Close stream |
| LLM API 5xx | HTTP status code | `error: {"error": "llm_unavailable"}` | Close stream |
| LLM API 401 | HTTP 401 | `error: {"error": "llm_auth_failed"}` | Close stream |
| Ollama unavailable | Connection error (localhost:11434) | `token: {"content": "[Using GPT-4o-mini as fallback] "}` | Retry with GPT-4o-mini |
| Client disconnect | `ConnectionResetError` | None | Cancel LLM call, cleanup |
| Token budget exceeded | Token count check | N/A | Exclude lowest-scored chunks |
| Invalid citation detected | Regex + source list check | None | Log warning (non-fatal) |

## Related ADRs
- ADR-008: Use Server-Sent Events for response streaming
- ADR-013: Switch from E2B to Ollama (Gemma 4 2B) for Local LLM (supersedes ADR-011)
- ADR-012: Remove general knowledge fallback
