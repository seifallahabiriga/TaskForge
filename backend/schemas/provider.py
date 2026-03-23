from dataclasses import dataclass, field

@dataclass
class CompletionRequest:
    prompt: str
    model_id: str
    max_tokens: int
    temperature: float
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


