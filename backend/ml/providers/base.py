from abc import ABC, abstractmethod
from backend.schemas.provider import (
    CompletionRequest,
    CompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse
)
from backend.core.exceptions import (
    ProviderError,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    AllProvidersFailedError,
)


class BaseProvider(ABC):
    """
    Contract every ML provider adapter must satisfy.
    Implement `complete` for text inference, `embed` for embeddings.
    Raise ProviderError (or subclass) on failures — the router catches it.
    """

    provider_name: str = "base"

    @abstractmethod
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """
        Run a text completion against the provider.
        Must raise ProviderError on any API or network failure.
        """
        ...

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Default — providers that don't support embeddings don't need to override.
        The router will skip to the next provider automatically.
        """
        raise ProviderUnavailableError(
            self.provider_name,
            f"{self.provider_name} does not support embeddings.",
        )

    @abstractmethod
    def is_available(self) -> bool:
        """
        Lightweight health check — returns False if the provider
        is misconfigured (e.g. missing API key) without making a network call.
        """
        ...