import json
from collections.abc import AsyncGenerator

import httpx

from foliun.config import Settings, get_settings
from foliun.errors import ApiError


class LlmClient:
    """OpenAI-compatible LLM client for Ollama and GPT-4o-mini."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize LLM client."""

        self.settings = settings or get_settings()

    def resolve_model(self, requested_model: str) -> tuple[str, str, dict[str, str]]:
        """Resolve request model to base URL, model name, and headers."""

        if requested_model == "gpt-4o-mini":
            if not self.settings.openai_api_key:
                raise ApiError(503, "service_unavailable", "Required service temporarily unavailable")
            return "https://api.openai.com/v1", "gpt-4o-mini", {"Authorization": f"Bearer {self.settings.openai_api_key}"}
        return self.settings.ollama_base_url.rstrip("/v1").rstrip("/"), self.settings.ollama_model, {}

    async def rewrite_query(self, query: str, requested_model: str) -> list[str]:
        """Generate three query variants."""

        base_url, model, headers = self.resolve_model(requested_model)
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Generate exactly three semantically diverse search query variants. Return one variant per line."},
                {"role": "user", "content": query},
            ],
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=1.5) as client:
            response = await client.post(f"{base_url}/v1/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        variants = [line.strip("- ").strip() for line in content.splitlines() if line.strip()]
        return variants[:3]

    async def stream_answer(self, requested_model: str, system_prompt: str, context: str, query: str) -> AsyncGenerator[str, None]:
        """Stream an LLM answer as text chunks."""

        base_url, model, headers = self.resolve_model(requested_model)
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{query}"},
            ],
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=self.settings.sse_timeout_seconds) as client:
            async with client.stream("POST", f"{base_url}/v1/chat/completions", json=payload, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line.removeprefix("data: ").strip()
                    if data == "[DONE]":
                        break
                    event = json.loads(data)
                    delta = event["choices"][0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content


def format_sse(event: str, data: dict[str, object]) -> str:
    """Format an SSE event."""

    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"
