# ADR-012: Remove General Knowledge Fallback in Favor of Grounded-Only Responses

## Status
Accepted

## Context
An earlier design included a "General Knowledge" fallback path: when no relevant documents were found (low retrieval confidence), the system would send the query to the LLM without context and return an ungrounded response. This contradicts the system's stated purpose as a "retrieval and knowledge processing system, not a chatbot wrapper."

The general knowledge path introduces hallucination risk, undermines citation reliability, and confuses the system's identity. Users expecting grounded answers may not realize when responses are ungrounded.

## Decision
We will **remove the general knowledge fallback** and replace it with an explicit "insufficient context" response.

- When no chunks exceed the cross-encoder confidence threshold (0.5), the system returns a structured response indicating no relevant documents were found
- No LLM call is made for the insufficient context path
- The response includes the query and suggests the user upload relevant documents
- The system never generates ungrounded answers

## Consequences

### Positive
- Eliminates hallucination risk from ungrounded LLM responses
- Maintains system integrity as a document-grounded retrieval system
- Users always know whether answers are sourced from their documents
- Simpler implementation — no branching logic for grounded vs ungrounded paths
- Reduces unnecessary LLM API costs for low-relevance queries

### Negative
- Users may perceive the system as "unhelpful" when no relevant documents exist
- Queries about general topics (not covered by uploaded documents) always return "no results"
- First-time users with no uploaded documents will always get "no results"

### Neutral
- Users can use ChatGPT or other chatbots directly for general knowledge queries
- A future "general knowledge with disclaimer" mode could be added as an opt-in feature
- The relevance threshold (0.5) may need calibration to balance false positives and false negatives

## Related ADRs
- ADR-006: Use cross-encoder ms-marco-MiniLM-L-6-v2 for reranking
- ADR-013: Switch from E2B to Ollama (Gemma 4 2B) for Local LLM (supersedes ADR-011)
