"""Centralized runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dotenv is a declared dependency
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_environment() -> None:
    if load_dotenv is not None:
        load_dotenv(PROJECT_ROOT / ".env", override=False)


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _as_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _as_float(value: str | None, default: float) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _resolve_path(value: str | None, default: str) -> Path:
    raw = value.strip() if value and value.strip() else default
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    project_root: Path
    zhipu_api_key: str
    zhipu_base_url: str
    zhipu_model: str
    llm_temperature: float
    llm_timeout: float
    llm_max_retries: int

    embedding_model_name: str
    embedding_device: str
    embedding_local_only: bool
    embedding_cache_dir: Path

    chroma_persist_dir: Path
    chroma_collection: str

    chunk_size: int
    chunk_overlap: int
    retrieval_top_k: int

    max_history_messages: int
    max_context_chars: int

    upload_dir: Path
    report_dir: Path
    eval_output_dir: Path

    gradio_server_name: str
    gradio_server_port: int
    gradio_share: bool

    @classmethod
    def from_env(cls) -> "Settings":
        _load_environment()

        chunk_size = max(100, _as_int(os.getenv("CHUNK_SIZE"), 500))
        chunk_overlap = max(0, _as_int(os.getenv("CHUNK_OVERLAP"), 100))
        if chunk_overlap >= chunk_size:
            chunk_overlap = max(0, chunk_size // 5)

        return cls(
            project_root=PROJECT_ROOT,
            zhipu_api_key=os.getenv("ZHIPU_API_KEY", "").strip(),
            zhipu_base_url=os.getenv(
                "ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"
            ).strip(),
            zhipu_model=os.getenv("ZHIPU_MODEL", "glm-4.7-flash").strip(),
            llm_temperature=max(
                0.0, min(1.0, _as_float(os.getenv("LLM_TEMPERATURE"), 0.2))
            ),
            llm_timeout=max(5.0, _as_float(os.getenv("LLM_TIMEOUT"), 60.0)),
            llm_max_retries=max(0, _as_int(os.getenv("LLM_MAX_RETRIES"), 2)),
            embedding_model_name=os.getenv(
                "EMBEDDING_MODEL_NAME", "BAAI/bge-small-zh"
            ).strip(),
            embedding_device=os.getenv("EMBEDDING_DEVICE", "cpu").strip() or "cpu",
            embedding_local_only=_as_bool(
                os.getenv("EMBEDDING_LOCAL_ONLY"), default=False
            ),
            embedding_cache_dir=_resolve_path(
                os.getenv("EMBEDDING_CACHE_DIR"), "./data/models"
            ),
            chroma_persist_dir=_resolve_path(
                os.getenv("CHROMA_PERSIST_DIR"), "./data/chroma"
            ),
            chroma_collection=os.getenv(
                "CHROMA_COLLECTION", "enterprise_knowledge"
            ).strip()
            or "enterprise_knowledge",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            retrieval_top_k=max(1, _as_int(os.getenv("RETRIEVAL_TOP_K"), 4)),
            max_history_messages=max(
                2, _as_int(os.getenv("MAX_HISTORY_MESSAGES"), 12)
            ),
            max_context_chars=max(
                2000, _as_int(os.getenv("MAX_CONTEXT_CHARS"), 14000)
            ),
            upload_dir=_resolve_path(os.getenv("UPLOAD_DIR"), "./data/uploads"),
            report_dir=_resolve_path(os.getenv("REPORT_DIR"), "./data/reports"),
            eval_output_dir=_resolve_path(
                os.getenv("EVAL_OUTPUT_DIR"), "./data/evaluations"
            ),
            gradio_server_name=os.getenv(
                "GRADIO_SERVER_NAME", "127.0.0.1"
            ).strip()
            or "127.0.0.1",
            gradio_server_port=max(
                1, _as_int(os.getenv("GRADIO_SERVER_PORT"), 7860)
            ),
            gradio_share=_as_bool(os.getenv("GRADIO_SHARE"), default=False),
        )

    def ensure_directories(self) -> None:
        """Create all runtime directories."""

        for path in (
            self.embedding_cache_dir,
            self.chroma_persist_dir,
            self.upload_dir,
            self.report_dir,
            self.eval_output_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def safe_summary(self) -> dict[str, Any]:
        """Return non-secret settings for UI status display."""

        key_configured = bool(
            self.zhipu_api_key
            and self.zhipu_api_key != "your_zhipu_api_key_here"
        )
        return {
            "model": self.zhipu_model,
            "api_key_configured": key_configured,
            "embedding_model": self.embedding_model_name,
            "embedding_local_only": self.embedding_local_only,
            "chroma_collection": self.chroma_collection,
            "chroma_dir": str(self.chroma_persist_dir),
            "retrieval_top_k": self.retrieval_top_k,
        }


def get_settings() -> Settings:
    """Create settings and ensure runtime directories exist."""

    settings = Settings.from_env()
    settings.ensure_directories()
    return settings
