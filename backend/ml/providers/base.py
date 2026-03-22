from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from core.exceptions import AllProvidersFailedError

# ------------------------------------------------------------------ #
# Provider I/O contracts                                              #
# ------------------------------------------------------------------ #

@dataclass
class CompletionRequest:
    prompt: str
    model_id: str
    max_tokens: int = 1024
    temperature: float = 0.7
    system_prompt: str | None = None
    extra_params: dict = field(default_factory=dict)


@dataclass
class CompletionResponse:
    text: str
    model_id: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float


@dataclass
class EmbeddingRequest:
    texts: list[str]
    model_id: str
    extra_params: dict = field(default_factory=dict)


@dataclass
class EmbeddingResponse:
    embeddings: list[list[float]]
    model_id: str
    provider: str
    token_count: int
    latency_ms: float


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


# ------------------------------------------------------------------ #
# Provider-level exceptions                                           #
# ------------------------------------------------------------------ #

class ProviderError(Exception):
    """Base class for all provider failures."""
    def __init__(self, provider: str, message: str):
        self.provider = provider
        super().__init__(f"[{provider}] {message}")


class ProviderAuthError(ProviderError):
    """Invalid or missing API key."""


class ProviderRateLimitError(ProviderError):
    """Provider is rate-limiting this account."""


class ProviderTimeoutError(ProviderError):
    """Provider did not respond within the allowed window."""


class ProviderUnavailableError(ProviderError):
    """Provider returned 5xx or is unreachable."""