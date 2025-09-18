"""Application configuration handling."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import yaml
from pydantic import BaseModel, Field, field_validator

ENV_PREFIX = "CTXC_"
DEFAULT_CONFIG_PATH = Path("~/.config/context-cache/config.yaml")

_YAML_KEY_MAP: Mapping[tuple[str, ...], str] = {
    ("storage", "db_path"): "db_path",
    ("storage", "use_faiss"): "use_faiss",
    ("embeddings", "model"): "embedding_model",
    ("embeddings", "rerank_model"): "rerank_model",
    ("embeddings", "rerank_enabled"): "rerank_enabled",
    ("retrieval", "top_k_dense"): "top_k_dense",
    ("retrieval", "top_k_final"): "top_k_final",
    ("retrieval", "mmr_lambda"): "mmr_lambda",
    ("watch", "include_glob"): "watch_include",
    ("watch", "exclude_glob"): "watch_exclude",
}


class Settings(BaseModel):
    """Runtime configuration loaded from YAML file and environment variables."""

    db_path: Path = Field(default=Path.home() / ".context-cache" / "cc.db")
    use_faiss: bool = True
    embedding_model: str = "intfloat/e5-small-v2"
    rerank_enabled: bool = True
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    mmr_lambda: float = 0.5
    top_k_dense: int = 100
    top_k_final: int = 8
    watch_include: str = "**/*.{md,txt,pdf,docx,eml,mbox}"
    watch_exclude: str = "**/{.git,.obsidian,node_modules}/**"

    model_config = {
        "validate_assignment": True,
        "extra": "ignore",
    }

    @field_validator("db_path", mode="before")
    @classmethod
    def _expand_db_path(cls, value: Any) -> Path:
        if isinstance(value, Path):
            return value.expanduser()
        if isinstance(value, str):
            return Path(value).expanduser()
        raise TypeError("db_path must be a path or string")

    @classmethod
    def from_yaml(cls, path: Path | None = None) -> "Settings":
        """Load YAML config and overlay env vars; fall back to defaults."""
        config_path = cls._resolve_config_path(path)
        data: dict[str, Any] = {}
        if config_path and config_path.exists():
            with config_path.open("r", encoding="utf-8") as fh:
                raw = yaml.safe_load(fh) or {}
            data.update(_flatten_yaml(raw))
        data.update(_load_env_overrides())
        return cls(**data)

    @staticmethod
    def _resolve_config_path(path: Path | None) -> Path | None:
        if path is not None:
            return path.expanduser()
        env_path = os.environ.get(f"{ENV_PREFIX}CONFIG")
        if env_path:
            return Path(env_path).expanduser()
        resolved_default = DEFAULT_CONFIG_PATH.expanduser()
        return resolved_default if resolved_default.exists() else None


def _flatten_yaml(raw: Mapping[str, Any], prefix: tuple[str, ...] = ()) -> dict[str, Any]:
    """Flatten nested YAML configuration to Settings field names."""
    flat: dict[str, Any] = {}
    for key, value in raw.items():
        next_prefix = prefix + (key,)
        if isinstance(value, Mapping):
            flat.update(_flatten_yaml(value, prefix=next_prefix))
        else:
            mapped_key = _YAML_KEY_MAP.get(next_prefix)
            if mapped_key:
                flat[mapped_key] = value
            elif key in Settings.model_fields:
                flat[key] = value
    return flat


def _load_env_overrides() -> dict[str, Any]:
    """Map environment variables with CTXC_ prefix into Settings fields."""
    overrides: dict[str, Any] = {}
    for key, value in os.environ.items():
        if not key.startswith(ENV_PREFIX):
            continue
        field_name = key[len(ENV_PREFIX) :].lower()
        if field_name in Settings.model_fields:
            overrides[field_name] = value
    return overrides


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor for dependency injection."""
    return Settings.from_yaml()


__all__ = ["Settings", "get_settings"]
