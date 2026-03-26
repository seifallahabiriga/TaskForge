import logging

from backend.ml.providers.base import BaseProvider
from backend.schemas.provider import (
    CompletionRequest,
    CompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
)
from backend.core.exceptions import ProviderError, AllProvidersFailedError

logger = logging.getLogger(__name__)


class ProviderRouter:
    """
    Executes completion and embedding requests against an ordered chain
    of providers. Each provider receives its own CompletionRequest so
    model_id is resolved per-provider — no provider ever receives another
    provider's model identifier.

    Usage:
        router = ProviderRouter(providers=[groq, gemini, huggingface])
        response = await router.complete({
            "groq": groq_request,
            "gemini": gemini_request,
            "huggingface": hf_request,
        })
    """

    def __init__(self, providers: list[BaseProvider]):
        if not providers:
            raise ValueError("ProviderRouter requires at least one provider.")
        self._providers = providers

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    async def complete(
        self,
        requests: dict[str, CompletionRequest],
    ) -> CompletionResponse:
        errors: list[ProviderError] = []

        for provider in self._providers:
            if not provider.is_available():
                logger.warning(
                    "provider.skip",
                    extra={"provider": provider.provider_name, "reason": "not_available"},
                )
                continue

            request = requests.get(provider.provider_name)
            if not request:
                logger.warning(
                    "provider.skip",
                    extra={"provider": provider.provider_name, "reason": "no_request_configured"},
                )
                continue

            try:
                response = await provider.complete(request)
                logger.info(
                    "provider.complete.success",
                    extra={
                        "provider": provider.provider_name,
                        "model_id": response.model_id,
                        "latency_ms": round(response.latency_ms, 1),
                    },
                )
                return response

            except ProviderError as exc:
                logger.warning(
                    "provider.complete.failed",
                    extra={"provider": provider.provider_name, "error": str(exc)},
                )
                errors.append(exc)

        raise AllProvidersFailedError(errors)

    async def embed(
        self,
        requests: dict[str, EmbeddingRequest],
    ) -> EmbeddingResponse:
        errors: list[ProviderError] = []

        for provider in self._providers:
            if not provider.is_available():
                logger.warning(
                    "provider.skip",
                    extra={"provider": provider.provider_name, "reason": "not_available"},
                )
                continue

            request = requests.get(provider.provider_name)
            if not request:
                logger.warning(
                    "provider.skip",
                    extra={"provider": provider.provider_name, "reason": "no_request_configured"},
                )
                continue

            try:
                response = await provider.embed(request)
                logger.info(
                    "provider.embed.success",
                    extra={
                        "provider": provider.provider_name,
                        "model_id": response.model_id,
                        "latency_ms": round(response.latency_ms, 1),
                    },
                )
                return response

            except ProviderError as exc:
                logger.warning(
                    "provider.embed.failed",
                    extra={"provider": provider.provider_name, "error": str(exc)},
                )
                errors.append(exc)

        raise AllProvidersFailedError(errors)