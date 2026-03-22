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


_BASE_URL = "https://api-inference.huggingface.co/models"
_TIMEOUT_SECONDS = 45          # HF cold-start can be slow on free tier


class HuggingFaceProvider(BaseProvider):
    """
    Fallback inference + embeddings provider.

    Uses the HuggingFace Hosted Inference API.
    - Text generation: POST /models/{model_id}  →  [{"generated_text": "..."}]
    - Embeddings:      POST /models/{model_id}  →  [[float, ...], ...]

    Model IDs are HF repo slugs, e.g.:
        "mistralai/Mistral-7B-Instruct-v0.2"
        "sentence-transformers/all-MiniLM-L6-v2"
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

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        prompt = self._build_prompt(request)
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": request.max_tokens,
                "temperature": request.temperature,
                "return_full_text": False,
                **request.extra_params,
            },
        }

        t0 = time.monotonic()
        raw = await self._post(request.model_id, payload)
        latency_ms = (time.monotonic() - t0) * 1000

        # HF returns a list: [{"generated_text": "..."}]
        if not isinstance(raw, list) or not raw:
            raise ProviderUnavailableError(
                self.provider_name, f"Unexpected response shape: {raw}"
            )

        text = raw[0].get("generated_text", "")

        return CompletionResponse(
            text=text,
            model_id=request.model_id,
            provider=self.provider_name,
            prompt_tokens=0,        # HF free tier does not return token counts
            completion_tokens=0,
            latency_ms=latency_ms,
        )

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        payload = {"inputs": request.texts, **request.extra_params}

        t0 = time.monotonic()
        raw = await self._post(request.model_id, payload)
        latency_ms = (time.monotonic() - t0) * 1000

        # HF returns list of embedding vectors
        if not isinstance(raw, list):
            raise ProviderUnavailableError(
                self.provider_name, f"Unexpected embedding response: {raw}"
            )

        return EmbeddingResponse(
            embeddings=raw,
            model_id=request.model_id,
            provider=self.provider_name,
            token_count=0,
            latency_ms=latency_ms,
        )

    def is_available(self) -> bool:
        return bool(self._api_key)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_prompt(request: CompletionRequest) -> str:
        """
        Flatten system + user into a single string for HF text-generation models.
        Instruct-tuned models expect a specific template (e.g. [INST]...[/INST]).
        For now we use a simple separator — swap in a Jinja template later
        once you add per-model prompt formatting.
        """
        if request.system_prompt:
            return f"{request.system_prompt}\n\n{request.prompt}"
        return request.prompt

    async def _post(self, model_id: str, payload: dict) -> list:
        try:
            response = await self._client.post(f"/{model_id}", json=payload)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(self.provider_name, str(exc)) from exc
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(self.provider_name, str(exc)) from exc

        return self._parse_response(response)

    def _parse_response(self, response: httpx.Response) -> list:
        if response.status_code == 401:
            raise ProviderAuthError(self.provider_name, "Invalid API token.")
        if response.status_code == 429:
            raise ProviderRateLimitError(self.provider_name, "Rate limit exceeded.")
        if response.status_code == 503:
            # HF returns 503 when model is loading (cold start)
            raise ProviderUnavailableError(
                self.provider_name,
                "Model is loading (cold start). Retry in a few seconds.",
            )
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