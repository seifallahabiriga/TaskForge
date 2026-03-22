import time
import httpx

from backend.core.config import settings
from backend.ml.providers.base import (
    BaseProvider,
    CompletionRequest,
    CompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)


_BASE_URL = "https://openrouter.ai/api/v1"
_TIMEOUT_SECONDS = 30


class OpenRouterProvider(BaseProvider):
    """
    Primary inference provider.

    OpenRouter exposes an OpenAI-compatible /chat/completions endpoint
    and routes to hundreds of open-source models (Llama 3, Mistral,
    DeepSeek, Qwen, etc.) via a single API key.

    Embeddings are NOT supported by OpenRouter — calls to `embed`
    raise ProviderUnavailableError so the router falls back to HF.
    """

    provider_name = "openrouter"

    def __init__(self):
        self._api_key = settings.OPENROUTER_API_KEY
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=_TIMEOUT_SECONDS,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "HTTP-Referer": settings.APP_URL,          # required by OpenRouter
                "X-Title": settings.APP_NAME,              # shown in OR dashboard
                "Content-Type": "application/json",
            },
        )

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        messages = self._build_messages(request)
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
        # OpenRouter does not provide an embeddings endpoint.
        # The router will catch this and delegate to HuggingFaceProvider.
        raise ProviderUnavailableError(
            self.provider_name,
            "OpenRouter does not support embeddings — use HuggingFaceProvider.",
        )

    def is_available(self) -> bool:
        return bool(self._api_key)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_messages(request: CompletionRequest) -> list[dict]:
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        return messages

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
            raise ProviderUnavailableError(
                self.provider_name,
                f"Server error {response.status_code}: {response.text[:200]}",
            )
        if response.status_code >= 400:
            raise ProviderUnavailableError(
                self.provider_name,
                f"Client error {response.status_code}: {response.text[:200]}",
            )

        return response.json()