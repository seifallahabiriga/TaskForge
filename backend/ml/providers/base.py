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

# ------------------------------------------------------------------ #
# Abstract base — all providers must implement these                  #
# ------------------------------------------------------------------ #

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

    @abstractmethod
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Generate embeddings for a list of texts.
        Must raise ProviderError on any API or network failure.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """
        Lightweight health check — returns False if the provider
        is misconfigured (e.g. missing API key) without making a network call.
        """
        ...