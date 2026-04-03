import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from backend.core.config import settings
from backend.repositories.model_version_repository import ModelVersionRepository
from backend.ml.providers.groq import GroqProvider
from backend.ml.providers.gemini import GeminiProvider
from backend.ml.providers.huggingface import HuggingFaceProvider
from backend.ml.providers.openrouter import OpenRouterProvider
from backend.ml.router import ProviderRouter
from backend.schemas.provider import (
    CompletionRequest,
    CompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
)
from backend.core.exceptions import (
    AllProvidersFailedError,
    ModelInferenceError,
)
from backend.core.enums import TaskType

logger = logging.getLogger(__name__)

# Ordered chain — first available provider that succeeds wins
_PROVIDER_CHAIN = ["groq", "gemini", "huggingface", "openrouter"]


class ModelService:

    def __init__(self):
        self.model_version_repo = ModelVersionRepository()
        self._router = ProviderRouter(
            providers=[
                GroqProvider(),         # primary   — fast, generous free tier
                GeminiProvider(),       # secondary — solid free tier
                HuggingFaceProvider(),  # fallback
                OpenRouterProvider(),   # last resort
            ]
        )

    # ------------------------------------------------------------------ #
    # Inference entry points (called by job_runner)                       #
    # ------------------------------------------------------------------ #

    async def run_inference(
        self,
        *,
        task_type: str,
        input_payload: dict,
        model_version_id: str | None = None,
    ) -> dict:
        """
        Opens its own DB session — called directly from job_runner as a
        coroutine, awaited inside tasks.py's single asyncio.run() loop.
        Returns a plain dict that result_service stores as output_payload.
        """
        async with self._make_session() as db:
            if task_type == TaskType.INFERENCE:
                return await self._run_completion(db, input_payload, model_version_id)

            if task_type == TaskType.ANALYSIS:
                return await self._run_analysis(db, input_payload, model_version_id)

        raise ModelInferenceError(
            f"Unsupported task type for ML inference: {task_type}"
        )

    # ------------------------------------------------------------------ #
    # Task-type handlers                                                  #
    # ------------------------------------------------------------------ #

    async def _run_completion(
        self,
        db: AsyncSession,
        input_payload: dict,
        model_version_id: str | None,
    ) -> dict:
        requests = await self._build_requests(
            db=db,
            task_type=TaskType.INFERENCE,
            input_payload=input_payload,
            model_version_id=model_version_id,
        )
        response = await self._complete_or_raise(requests)
        return {
            "text": response.text,
            "model_id": response.model_id,
            "provider": response.provider,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "latency_ms": response.latency_ms,
        }

    async def _run_analysis(
        self,
        db: AsyncSession,
        input_payload: dict,
        model_version_id: str | None,
    ) -> dict:
        requests = await self._build_requests(
            db=db,
            task_type=TaskType.ANALYSIS,
            input_payload=input_payload,
            model_version_id=model_version_id,
            default_system_prompt="You are an expert analyst. Respond only with a valid JSON object.",
        )
        response = await self._complete_or_raise(requests)
        return {
            "analysis": response.text,
            "model_id": response.model_id,
            "provider": response.provider,
            "latency_ms": response.latency_ms,
        }

    # ------------------------------------------------------------------ #
    # Embedding (standalone, not tied to a task type yet)                 #
    # ------------------------------------------------------------------ #

    async def embed(
        self,
        *,
        texts: list[str],
        model_version_id: str | None = None,
    ) -> EmbeddingResponse:
        async with self._make_session() as db:
            requests = {}
            for provider_name in _PROVIDER_CHAIN:
                model_version = await self.model_version_repo.get_default_for_provider_and_task_type(
                    db, provider_name, "embedding"
                )
                if model_version:
                    requests[provider_name] = EmbeddingRequest(
                        texts=texts,
                        model_id=model_version.model_id,
                    )

        if not requests:
            raise ModelInferenceError("No embedding models configured.")

        try:
            return await self._router.embed(requests)
        except AllProvidersFailedError as exc:
            raise ModelInferenceError(
                f"Embedding failed across all providers: {exc}"
            ) from exc

    # ------------------------------------------------------------------ #
    # Per-provider request building                                       #
    # ------------------------------------------------------------------ #

    async def _build_requests(
        self,
        db: AsyncSession,
        task_type: str,
        input_payload: dict,
        model_version_id: str | None,
        default_system_prompt: str | None = None,
    ) -> dict[str, CompletionRequest]:
        """
        Resolves one model per provider and builds a CompletionRequest
        for each. The router will try them in chain order, each with
        its own correct model_id.
        """
        system_prompt = input_payload.get("system_prompt", default_system_prompt)
        requests = {}

        for provider_name in _PROVIDER_CHAIN:
            model_version = await self._resolve_model_for_provider(
                db=db,
                provider_name=provider_name,
                task_type=task_type,
                explicit_model_version_id=model_version_id,
            )
            if model_version:
                requests[provider_name] = CompletionRequest(
                    prompt=input_payload["prompt"],
                    model_id=model_version.model_id,
                    max_tokens=input_payload.get("max_tokens", 1024),
                    temperature=input_payload.get("temperature", 0.7),
                    system_prompt=system_prompt,
                    extra_params=input_payload.get("extra_params", {}),
                )

        if not requests:
            raise ModelInferenceError(
                f"No models configured for task type '{task_type}'."
            )

        return requests

    # ------------------------------------------------------------------ #
    # Model version resolution                                            #
    # ------------------------------------------------------------------ #

    async def _resolve_model_for_provider(
        self,
        db: AsyncSession,
        provider_name: str,
        task_type: str,
        explicit_model_version_id: str | None,
    ):
        """
        If an explicit model_version_id is given and belongs to this provider,
        use it. Otherwise fall back to the active model for this provider+task_type.
        Returns None if no model is configured for this provider — caller skips it.
        """
        if explicit_model_version_id:
            model_version = await self.model_version_repo.get_by_id(
                db, explicit_model_version_id
            )
            if model_version and model_version.provider == provider_name:
                return model_version

        return await self.model_version_repo.get_default_for_provider_and_task_type(
            db, provider_name, task_type
        )

    # ------------------------------------------------------------------ #
    # Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    async def _complete_or_raise(
        self,
        requests: dict[str, CompletionRequest],
    ) -> CompletionResponse:
        try:
            return await self._router.complete(requests)
        except AllProvidersFailedError as exc:
            logger.error(
                "model_service.inference.all_failed",
                extra={"errors": str(exc)},
            )
            raise ModelInferenceError(
                f"Inference failed across all providers: {exc}"
            ) from exc

    @staticmethod
    def _make_session():
        engine = create_async_engine(settings.DATABASE_ASYNC_URL, pool_pre_ping=True)
        factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
        return factory()