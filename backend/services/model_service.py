import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from backend.core.config import settings
from backend.repositories.model_version_repository import ModelVersionRepository
from backend.ml.providers.openrouter import OpenRouterProvider
from backend.ml.providers.huggingface import HuggingFaceProvider
from backend.ml.router import ProviderRouter
from backend.ml.providers.base import (
    CompletionRequest,
    CompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse
)
from backend.core.exceptions import AllProvidersFailedError

from backend.core.enums import TaskType
from backend.core.exceptions import (
    ModelNotFoundError,
    ModelInferenceError,
)

logger = logging.getLogger(__name__)


class ModelService:

    def __init__(self):
        self.model_version_repo = ModelVersionRepository()
        self._router = ProviderRouter(
            providers=[
                OpenRouterProvider(),     # primary
                HuggingFaceProvider(),    # fallback
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
        model_version = await self._resolve_model(db, model_version_id, TaskType.INFERENCE)

        request = CompletionRequest(
            prompt=input_payload["prompt"],
            model_id=model_version.model_id,
            max_tokens=input_payload.get("max_tokens", settings.API_INFERENCE_TOKEN_LIMIT),
            temperature=input_payload.get("temperature", settings.API_INFERENCE_TEMPERATURE),
            system_prompt=input_payload.get("system_prompt"),
            extra_params=input_payload.get("extra_params", {}),
        )

        response = await self._complete_or_raise(request)

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
        """
        Analysis tasks send a structured prompt and expect a JSON-parseable
        response from the model. Expand as needed (classification,
        summarisation, extraction, etc.).
        """
        model_version = await self._resolve_model(db, model_version_id, TaskType.ANALYSIS)

        system_prompt = input_payload.get(
            "system_prompt",
            "You are an expert analyst. Respond only with a valid JSON object.",
        )
        request = CompletionRequest(
            prompt=input_payload["prompt"],
            model_id=model_version.model_id,
            max_tokens=input_payload.get("max_tokens", settings.API_ANALYSIS_TOKEN_LIMIT),
            temperature=input_payload.get("temperature", settings.API_ANALYSIS_TEMPERATURE),
            system_prompt=system_prompt,
            extra_params=input_payload.get("extra_params", {}),
        )

        response = await self._complete_or_raise(request)

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
            model_version = await self._resolve_model(db, model_version_id, task_type="embedding")

        request = EmbeddingRequest(
            texts=texts,
            model_id=model_version.model_id,
        )

        try:
            return await self._router.embed(request)
        except AllProvidersFailedError as exc:
            raise ModelInferenceError(
                f"Embedding failed across all providers: {exc}"
            ) from exc

    # ------------------------------------------------------------------ #
    # Model version resolution                                            #
    # ------------------------------------------------------------------ #

    async def _resolve_model(
        self,
        db: AsyncSession,
        model_version_id: str | None,
        task_type: str,
    ):
        if model_version_id:
            model_version = await self.model_version_repo.get_by_id(db, model_version_id)
            if not model_version:
                raise ModelNotFoundError(
                    f"ModelVersion {model_version_id} not found."
                )
            return model_version

        model_version = await self.model_version_repo.get_default_for_task_type(
            db, task_type
        )
        if not model_version:
            raise ModelNotFoundError(
                f"No default model configured for task type '{task_type}'. "
                "Seed the model_versions table or pass an explicit model_version_id."
            )
        return model_version

    # ------------------------------------------------------------------ #
    # Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    async def _complete_or_raise(self, request: CompletionRequest) -> CompletionResponse:
        try:
            return await self._router.complete(request)
        except AllProvidersFailedError as exc:
            logger.error(
                "model_service.inference.all_failed",
                extra={"model_id": request.model_id, "errors": str(exc)},
            )
            raise ModelInferenceError(
                f"Inference failed across all providers: {exc}"
            ) from exc

    @staticmethod
    def _make_session():
        engine = create_async_engine(settings.DATABASE_ASYNC_URL, pool_pre_ping=True)
        factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
        return factory()