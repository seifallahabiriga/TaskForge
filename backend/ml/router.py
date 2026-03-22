import logging

from backend.ml.providers.base import (
    BaseProvider,
    CompletionRequest,
    CompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ProviderError
)
from backend.core.exceptions import AllProvidersFailedError

logger = logging.getLogger(__name__)


class ProviderRouter:
    """
    Executes completion and embedding requests against an ordered chain
    of providers.  The first provider that succeeds wins.  If a provider
    raises any ProviderError the router logs the failure, records it, and
    moves on to the next provider.  When every provider fails it raises
    AllProvidersFailedError with the full error list attached.

    Usage:
        router = ProviderRouter(providers=[openrouter, huggingface])
        response = await router.complete(request)
    """

    def __init__(self, providers: list[BaseProvider]):
        if not providers:
            raise ValueError("ProviderRouter requires at least one provider.")
        self._providers = providers

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        errors: list[ProviderError] = []

        for provider in self._providers:
            if not provider.is_available():
                logger.warning(
                    "provider.skip",
                    extra={"provider": provider.provider_name, "reason": "not_available"},
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

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        errors: list[ProviderError] = []

        for provider in self._providers:
            if not provider.is_available():
                logger.warning(
                    "provider.skip",
                    extra={"provider": provider.provider_name, "reason": "not_available"},
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