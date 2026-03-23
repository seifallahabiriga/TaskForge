import time
import httpx

from backend.core.config import settings
from backend.ml.providers.base import BaseProvider
from backend.schemas.provider import (
    CompletionRequest, CompletionResponse,
    EmbeddingRequest, EmbeddingResponse,
)
from backend.core.exceptions import (
    ProviderAuthError, ProviderRateLimitError,
    ProviderTimeoutError, ProviderUnavailableError,
)

_BASE_URL = "https://router.huggingface.co/v1"
_TIMEOUT_SECONDS = 45


class HuggingFaceProvider(BaseProvider):
    """
    Fallback inference provider using HuggingFace's OpenAI-compatible router.
    Endpoint: https://router.huggingface.co/v1/chat/completions
    """

    provider_name = "huggingface"

    def __init__(self):
        self._api_key = settings.HUGGINGFACE_API_KEY
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=_TIMEOUT_SECONDS,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )

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

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        payload = {"inputs": request.texts, **request.extra_params}

        t0 = time.monotonic()
        raw = await self._post_raw(f"/pipeline/feature-extraction/{request.model_id}", payload)
        latency_ms = (time.monotonic() - t0) * 1000

        return EmbeddingResponse(
            embeddings=raw,
            model_id=request.model_id,
            provider=self.provider_name,
            token_count=0,
            latency_ms=latency_ms,
        )

    def is_available(self) -> bool:
        return bool(self._api_key)

    async def _post(self, path: str, payload: dict) -> dict:
        try:
            response = await self._client.post(path, json=payload)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(self.provider_name, str(exc)) from exc
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(self.provider_name, str(exc)) from exc
        return self._parse_response(response)

    async def _post_raw(self, path: str, payload: dict) -> list:
        try:
            response = await self._client.post(path, json=payload)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(self.provider_name, str(exc)) from exc
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(self.provider_name, str(exc)) from exc
        return self._parse_response(response)

    def _parse_response(self, response: httpx.Response):
        if response.status_code == 401:
            raise ProviderAuthError(self.provider_name, "Invalid API token.")
        if response.status_code == 429:
            raise ProviderRateLimitError(self.provider_name, "Rate limit exceeded.")
        if response.status_code == 503:
            raise ProviderUnavailableError(self.provider_name, "Model loading (cold start).")
        if response.status_code >= 500:
            raise ProviderUnavailableError(self.provider_name, f"Server error {response.status_code}: {response.text[:200]}")
        if response.status_code >= 400:
            raise ProviderUnavailableError(self.provider_name, f"Client error {response.status_code}: {response.text[:200]}")
        return response.json()