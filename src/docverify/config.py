"""Configuration.

Precedence, lowest to highest:

    field defaults  <  YAML file  <  environment variables

Environment variables use the ``DV__`` prefix and ``__`` as the nesting
separator, so a Docker invocation can override any single value without
touching the file::

    docker run -e DV__STAGES__INVESTIGATE__CONCURRENCY=16 ...

This is deliberately the same shape a Kubernetes ConfigMap plus ``env:``
entries would take, so moving there later changes no code. Nothing here is
Kubernetes-specific and no Kubernetes manifests exist in this repository.

Secrets do NOT belong in the YAML file. They come from the environment; see
``.env.example``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class LimiterConfig(BaseModel):
    """Global throttle on LLM calls.

    This is the only load control that matters. Processing documents one at a
    time does NOT bound load, because the fan-out to parallel claims happens
    inside a document. Put the throttle where the constrained resource is.
    """

    max_in_flight: int = Field(default=8, ge=1)
    requests_per_second: float = Field(default=4.0, gt=0)


class ProviderConfig(BaseModel):
    """One LLM endpoint.

    ``kind`` selects the adapter in ``docverify.llm.providers``. Internal
    vLLM/TGI deployments and most hosted APIs speak the OpenAI
    chat-completions shape, so ``openai_compat`` covers the common case.
    """

    kind: Literal["openai_compat", "gemini", "fake"] = "openai_compat"
    base_url: str | None = None
    model: str = ""
    api_key_env: str | None = None
    """Name of the environment variable holding the key. Never the key itself."""
    timeout_s: float = 120.0
    max_retries: int = 3
    schema_retries: int = 2
    """Retries specifically for malformed structured output. Quantised models
    produce invalid JSON more often than they reason badly; handle it once
    here rather than in every stage."""


class LLMConfig(BaseModel):
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)
    default_provider: str = "fake"
    limiter: LimiterConfig = Field(default_factory=LimiterConfig)


class TracingConfig(BaseModel):
    """Langfuse. Optional by design.

    Traces and agent reasoning go to Langfuse. State and results go to the
    store. Nothing the product depends on may live only in a trace.
    """

    enabled: bool = False
    host_env: str = "LANGFUSE_HOST"
    public_key_env: str = "LANGFUSE_PUBLIC_KEY"
    secret_key_env: str = "LANGFUSE_SECRET_KEY"


class StageConfig(BaseModel):
    """Per-stage knobs. Every stage gets its own concurrency and its own
    provider, because the stages are bound by different resources."""

    concurrency: int = Field(default=4, ge=1)
    provider: str | None = None
    """Falls back to ``llm.default_provider`` when unset."""
    prompt_version: str = "v1"
    temperature: float = 0.0
    max_tokens: int = 2048
    timeout_s: float = 180.0
    max_attempts: int = Field(default=3, ge=1)


class InvestigateConfig(StageConfig):
    max_tool_calls: int = Field(default=20, ge=1)
    """Hard ceiling per claim. Exhausting it yields UNVERIFIABLE with reason
    TOOL_BUDGET_EXHAUSTED, never a guessed answer."""

    samples: int = Field(default=1, ge=1)
    """Run the investigator N times and treat disagreement as an
    UNVERIFIABLE signal. Roadmap item; keep at 1 until a labelled set exists
    to measure whether it helps."""


class EvidenceConfig(StageConfig):
    max_span_lines: int = Field(default=400, ge=1)
    """A citation spanning more than this many lines is not evidence, it is a
    gesture at a file. Fails the authenticity check."""

    require_at_least_one: bool = True
    """An answer with no citations cannot be verified, whatever it says."""


class StagesConfig(BaseModel):
    classify: StageConfig = Field(default_factory=StageConfig)
    investigate: InvestigateConfig = Field(default_factory=InvestigateConfig)
    evidence: EvidenceConfig = Field(default_factory=EvidenceConfig)
    judge: StageConfig = Field(default_factory=StageConfig)


class IngestConfig(BaseModel):
    max_file_mb: float = 25.0
    accept_formats: list[str] = Field(default=["docx", "pdf", "html", "md", "txt"])
    reject_scanned_pdf: bool = True
    """A PDF with no extractable text layer is rejected with a clear error.
    Silently generating claims from OCR-less garbage is worse than refusing."""

    min_extractable_chars_per_page: int = 40
    """Below this, a PDF page is treated as scanned."""


class CodeToolsConfig(BaseModel):
    kind: Literal["mcp", "fake"] = "fake"
    repo: str = ""
    branch: str = "main"
    """Resolved to a commit SHA once at run start. Every tool call and every
    CodeRef in the run uses that SHA, never the branch name."""

    mcp_url_env: str = "DV_CODETOOLS_MCP_URL"
    mcp_token_env: str = "DV_CODETOOLS_MCP_TOKEN"
    timeout_s: float = 60.0


class StoreConfig(BaseModel):
    kind: Literal["sqlite"] = "sqlite"
    dsn: str = "data/docverify.db"


class BusConfig(BaseModel):
    kind: Literal["inmemory"] = "inmemory"
    max_queue_size: int = 10_000


class RunConfig(BaseModel):
    docs_concurrency: int = Field(default=1, ge=1)
    """How many documents are processed at once. A throughput knob, not a
    safety mechanism; the LLM limiter is what bounds load."""

    fail_run_on_doc_error: bool = False


class ApiConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


class Config(BaseSettings):
    """The whole configuration."""

    model_config = SettingsConfigDict(
        env_prefix="DV__",
        env_nested_delimiter="__",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Put environment variables ahead of init values.

        `load_config` passes the YAML file's contents as init kwargs, and
        pydantic-settings ranks init above env by default. That would make
        `DV__STAGES__INVESTIGATE__CONCURRENCY=16` silently do nothing whenever
        the key also appears in the YAML, which is exactly when someone
        reaches for it. Reordering gives the documented precedence:

            field defaults  <  YAML file  <  environment
        """
        return (env_settings, dotenv_settings, init_settings, file_secret_settings)

    run: RunConfig = Field(default_factory=RunConfig)
    ingest: IngestConfig = Field(default_factory=IngestConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    tracing: TracingConfig = Field(default_factory=TracingConfig)
    codetools: CodeToolsConfig = Field(default_factory=CodeToolsConfig)
    store: StoreConfig = Field(default_factory=StoreConfig)
    bus: BusConfig = Field(default_factory=BusConfig)
    stages: StagesConfig = Field(default_factory=StagesConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)
    prompts_dir: str = "prompts"
    log_level: str = "INFO"
    log_json: bool = False

    def snapshot(self) -> dict[str, Any]:
        """The effective config, for storing on the run.

        A result that cannot be explained after someone edits the config file
        is not a result you can defend.
        """
        return self.model_dump(mode="json")

    def provider_for(self, stage: str) -> ProviderConfig:
        """Resolve the provider a stage should use."""
        stage_cfg: StageConfig = getattr(self.stages, stage)
        name = stage_cfg.provider or self.llm.default_provider
        if name not in self.llm.providers:
            raise KeyError(
                f"stage {stage!r} asks for provider {name!r}, which is not in llm.providers"
            )
        return self.llm.providers[name]


def load_config(path: str | Path | None = None) -> Config:
    """Load YAML (if given), then let environment variables override it."""
    data: dict[str, Any] = {}
    if path is not None:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"config file not found: {p}")
        loaded = yaml.safe_load(p.read_text(encoding="utf-8"))
        if loaded:
            data = loaded
    return Config(**data)
