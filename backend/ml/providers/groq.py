import time
import httpx

from backend.core.config import settings
from backend.ml.providers.base import BaseProvider
from backend.schemas.provider import (
    CompletionRequest,
    CompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
)
from backend.core.exceptions import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

_BASE_URL = "https://api.groq.com/openai/v1"
_TIMEOUT_SECONDS = 30


class GroqProvider(BaseProvider):
    """
    Primary inference provider.
    OpenAI-compatible API, extremely fast inference via LPU hardware.
    Free tier: 30 RPM, 14,400 RPD on llama-3.1-8b-instant.
    """

    provider_name = "groq"

    def __init__(self):
        self._api_key = settings.GROQ_API_KEY
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=_TIMEOUT_SECONDS,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        payload = {
            "model": request.model_id,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            **request.extra_params,
        }

        t0 = time.monotonic()
        raw = await self._post("/chat/completions", payload)
        latency_ms = (time.monotonic() - t0) * 1000

        choice = raw["choices"][0]
        usage = raw.get("usage", {})

        return CompletionResponse(
            text=choice["message"]["content"],
            model_id=raw.get("model", request.model_id),
            provider=self.provider_name,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            latency_ms=latency_ms,
        )

    def is_available(self) -> bool:
        return bool(self._api_key)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    async def _post(self, path: str, payload: dict) -> dict:
        try:
            response = await self._client.post(path, json=payload)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(self.provider_name, str(exc)) from exc
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(self.provider_name, str(exc)) from exc
        return self._parse_response(response)

    def _parse_response(self, response: httpx.Response) -> dict:
        if response.status_code == 401:
            raise ProviderAuthError(self.provider_name, "Invalid API key.")
        if response.status_code == 429:
            raise ProviderRateLimitError(self.provider_name, "Rate limit exceeded.")
        if response.status_code >= 500:
            raise ProviderUnavailableError(self.provider_name, f"Server error {response.status_code}: {response.text[:200]}")
        if response.status_code >= 400:
            raise ProviderUnavailableError(self.provider_name, f"Client error {response.status_code}: {response.text[:200]}")
        return response.json()