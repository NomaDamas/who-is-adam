"""Environment-backed runtime configuration."""

from __future__ import annotations

import os
from enum import StrEnum
from typing import Mapping

from pydantic import BaseModel, Field, HttpUrl, PositiveFloat, field_validator, model_validator


class LlmProvider(StrEnum):
    FAKE = "fake"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    CUSTOM_HTTP = "custom_http"


class ProviderMode(StrEnum):
    OFFLINE = "offline"
    HOSTED = "hosted"


class HttpProviderConfig(BaseModel):
    base_url: HttpUrl
    timeout_seconds: PositiveFloat = 30
    max_retries: int = Field(default=2, ge=0)
    api_key: str | None = None


class LlmConfig(BaseModel):
    provider: LlmProvider = LlmProvider.FAKE
    model: str | None = None
    api_key: str | None = None
    base_url: HttpUrl | None = None
    timeout_seconds: PositiveFloat = 60
    max_retries: int = Field(default=1, ge=0)
    supports_json_schema: bool = True

    @model_validator(mode="after")
    def validate_provider_requirements(self) -> "LlmConfig":
        if self.provider is LlmProvider.FAKE:
            return self
        missing = []
        if not self.model:
            missing.append("WHO_IS_ADAM_LLM_MODEL")
        if not self.api_key:
            missing.append("WHO_IS_ADAM_LLM_API_KEY")
        if self.provider is LlmProvider.CUSTOM_HTTP and self.base_url is None:
            missing.append("WHO_IS_ADAM_LLM_BASE_URL")
        if not self.supports_json_schema:
            missing.append("WHO_IS_ADAM_LLM_SUPPORTS_JSON_SCHEMA")
        if missing:
            raise ValueError(
                "hosted LLM providers require model, API key, JSON-schema output support, "
                f"and custom_http base URL when applicable: {', '.join(missing)}"
            )
        return self


class ReviewConfig(BaseModel):
    offline: bool = False
    llm: LlmConfig = Field(default_factory=LlmConfig)
    openreview: HttpProviderConfig = Field(
        default_factory=lambda: HttpProviderConfig.model_validate(
            {"base_url": "https://api2.openreview.net"}
        )
    )
    semantic_scholar: HttpProviderConfig = Field(
        default_factory=lambda: HttpProviderConfig.model_validate(
            {"base_url": "https://api.semanticscholar.org/graph/v1"}
        )
    )
    crossref: HttpProviderConfig = Field(
        default_factory=lambda: HttpProviderConfig.model_validate(
            {"base_url": "https://api.crossref.org"}
        )
    )
    arxiv: HttpProviderConfig = Field(
        default_factory=lambda: HttpProviderConfig.model_validate(
            {"base_url": "https://export.arxiv.org/api/query"}
        )
    )
    crossref_mailto: str | None = None
    ocr_enabled: bool = False
    tesseract_cmd: str | None = None
    fixed_run_timestamp: str | None = None
    random_seed: int = 0

    @field_validator("fixed_run_timestamp", "crossref_mailto", "tesseract_cmd", mode="before")
    @classmethod
    def empty_string_is_none(cls, value: object) -> object:
        return None if value == "" else value

    @property
    def provider_mode(self) -> ProviderMode:
        return ProviderMode.OFFLINE if self.offline or self.llm.provider is LlmProvider.FAKE else ProviderMode.HOSTED

    @model_validator(mode="after")
    def force_fake_llm_when_offline(self) -> "ReviewConfig":
        if self.offline and self.llm.provider is not LlmProvider.FAKE:
            self.llm = self.llm.model_copy(update={"provider": LlmProvider.FAKE})
        return self

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "ReviewConfig":
        values = os.environ if env is None else env
        offline = _bool(values.get("WHO_IS_ADAM_OFFLINE"), default=False)
        llm_provider: LlmProvider | str = LlmProvider.FAKE if offline else values.get("WHO_IS_ADAM_LLM_PROVIDER", LlmProvider.FAKE)
        return cls.model_validate(
            {
                "offline": offline,
                "llm": {
                    "provider": llm_provider,
                    "model": _none_empty(values.get("WHO_IS_ADAM_LLM_MODEL")),
                    "api_key": _none_empty(values.get("WHO_IS_ADAM_LLM_API_KEY")),
                    "base_url": _none_empty(values.get("WHO_IS_ADAM_LLM_BASE_URL")),
                    "timeout_seconds": _float(values.get("WHO_IS_ADAM_LLM_TIMEOUT_SECONDS"), 60),
                    "max_retries": _int(values.get("WHO_IS_ADAM_LLM_MAX_RETRIES"), 1),
                    "supports_json_schema": _bool(
                        values.get("WHO_IS_ADAM_LLM_SUPPORTS_JSON_SCHEMA"), default=True
                    ),
                },
                "openreview": _http(values, "OPENREVIEW", "https://api2.openreview.net"),
                "semantic_scholar": _http(
                    values, "SEMANTIC_SCHOLAR", "https://api.semanticscholar.org/graph/v1"
                ),
                "crossref": _http(values, "CROSSREF", "https://api.crossref.org"),
                "arxiv": _http(values, "ARXIV", "https://export.arxiv.org/api/query"),
                "crossref_mailto": _none_empty(values.get("WHO_IS_ADAM_CROSSREF_MAILTO")),
                "ocr_enabled": _bool(values.get("WHO_IS_ADAM_OCR_ENABLED"), default=False),
                "tesseract_cmd": _none_empty(values.get("WHO_IS_ADAM_TESSERACT_CMD")),
                "fixed_run_timestamp": _none_empty(values.get("WHO_IS_ADAM_FIXED_RUN_TIMESTAMP")),
                "random_seed": _int(values.get("WHO_IS_ADAM_RANDOM_SEED"), 0),
            }
        )


def _http(env: Mapping[str, str], name: str, default_url: str) -> HttpProviderConfig:
    return HttpProviderConfig.model_validate(
        {
            "base_url": env.get(f"WHO_IS_ADAM_{name}_BASE_URL", default_url),
            "timeout_seconds": _float(env.get(f"WHO_IS_ADAM_{name}_TIMEOUT_SECONDS"), 30),
            "max_retries": _int(env.get(f"WHO_IS_ADAM_{name}_MAX_RETRIES"), 2),
            "api_key": _none_empty(env.get(f"WHO_IS_ADAM_{name}_API_KEY")),
        }
    )


def _none_empty(value: str | None) -> str | None:
    return None if value is None or value == "" else value


def _int(value: str | None, default: int) -> int:
    return default if value in (None, "") else int(value)


def _float(value: str | None, default: float) -> float:
    return default if value in (None, "") else float(value)


def _bool(value: str | None, *, default: bool) -> bool:
    if value in (None, ""):
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean environment value: {value!r}")
