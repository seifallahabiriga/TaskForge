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

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
_TIMEOUT_SECONDS = 30


class GeminiProvider(BaseProvider):
    """
    Secondary inference provider.
    Uses Google's Gemini REST API directly (not OpenAI-compatible).
    Free tier: gemini-2.5-flash at 10 RPM, 500 RPD.
    """

    provider_name = "gemini"

    def __init__(self):
        self._api_key = settings.GEMINI_API_KEY
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=_TIMEOUT_SECONDS,
        )

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        contents = []

        # Gemini uses a different structure for system prompt
        system_instruction = None
        if request.system_prompt:
            system_instruction = {"parts": [{"text": request.system_prompt}]}

        contents.append({
            "role": "user",
            "parts": [{"text": request.prompt}],
        })

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": request.max_tokens,
                "temperature": request.temperature,
                **request.extra_params,
            },
        }
        if system_instruction:
            payload["system_instruction"] = system_instruction

        t0 = time.monotonic()
        raw = await self._post(request.model_id, payload)
        latency_ms = (time.monotonic() - t0) * 1000

        candidate = raw["candidates"][0]
        text = candidate["content"]["parts"][0]["text"]
        usage = raw.get("usageMetadata", {})

        return CompletionResponse(
            text=text,
            model_id=request.model_id,
            provider=self.provider_name,
            prompt_tokens=usage.get("promptTokenCount", 0),
            completion_tokens=usage.get("candidatesTokenCount", 0),
            latency_ms=latency_ms,
        )

    def is_available(self) -> bool:
        return bool(self._api_key)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    async def _post(self, model_id: str, payload: dict) -> dict:
        url = f"/models/{model_id}:generateContent"
        try:
            response = await self._client.post(
                url,
                json=payload,
                params={"key": self._api_key},
            )
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