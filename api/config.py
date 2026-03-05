__pattern__ = "Configuration"

from enum import StrEnum

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AcornMode(StrEnum):
    DGX   = "dgx"
    MINI  = "mini"
    CLOUD = "cloud"


class RoutingStrategy(StrEnum):
    PASSTHROUGH  = "passthrough"
    STALL        = "stall"
    CONFIDENCE   = "confidence"
    COUNCIL      = "council"


class AcornSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8",
                                      extra="ignore", case_sensitive=False)

    # -- Platform -----------------------------------------------------------------
    acorn_mode: AcornMode = AcornMode.DGX
    acorn_root: str = "/app"
    acorn_workspace_base: str = "/workspaces"
    acorn_network: str = "acorn_acorn-net"

    # -- Inference ----------------------------------------------------------------
    anthropic_base_url: str     = "http://acorn-api-relay:9000"
    anthropic_auth_token: str   = "ollama"
    anthropic_api_key: str      = ""          # Empty = local-only
    anthropic_api_key_real: str = ""          # Used by proxy for escalation
    default_model: str          = "llama3.3:70b"
    coder_model: str            = "qwen3-coder"
    analysis_model: str         = "deepseek-r1:14b"
    reasoning_model: str        = "deepseek-r1:14b"

    # -- Routing strategy ---------------------------------------------------------
    routing_strategy: RoutingStrategy = RoutingStrategy.PASSTHROUGH
    stall_detection_enabled: bool     = False
    stall_min_tokens: int             = 20
    stall_phrases: list[str]          = Field(
        default=["i cannot", "i don't know how", "i'm unable", "as an ai"])
    local_confidence_threshold: float = 0.8
    council_models: list[str] = Field(default=["qwen3-coder", "deepseek-r1:14b"])
    council_judge_model: str = "deepseek-r1:14b"

    # -- Resource caps ------------------------------------------------------------
    max_agents_per_problem: int   = 10
    max_concurrent_problems: int  = 3
    max_harness_containers: int   = 20

    # -- Embeddings ---------------------------------------------------------------
    ollama_base_url: str = "http://acorn-ollama:11434"
    embed_model: str = "nomic-embed-text"
    embed_dim: int = 768

    # -- Memory -------------------------------------------------------------------
    database_url: str                 = "postgresql://acorn:acorn@acorn-postgres:5432/acorn"
    redis_url: str                    = "redis://acorn-redis:6379"
    acorn_session_ttl_hours: int      = 24
    acorn_memory_ttl_days: int        = 90

    # -- Kernel grove -------------------------------------------------------------
    acorn_kernel_promo_threshold: int = 2
    kernel_deprecation_threshold: float = 0.4
    kernel_probationary_path: str     = "/workspace/kernels/probationary"
    kernel_permanent_path: str        = "/workspace/kernels/permanent"

    # -- Agent behaviour ----------------------------------------------------------
    stale_threshold_seconds: int      = 1800
    warden_poll_interval: int         = 60
    acorn_idle_timeout_seconds: int   = 120
    claude_code_experimental_agent_teams: str = "1"

    # -- Observability ------------------------------------------------------------
    telemetry_enabled: bool           = True
    stall_escalation_alert_threshold: float = 0.3   # Alert if > 30% of calls escalate

    # -- CORTEX+ (Layer 5 cognitive kernel, GWT) ------------------------------------
    cortex_enabled: bool               = False
    cortex_tick_interval: int          = 120

    # -- API (for CORTEX+ self-calls) ----------------------------------------------
    port: int                         = 8000

    # -- Builder (disabled; WARDEN replaces builder, infra-only, no LLM) ----------
    builder_enabled: bool              = False
    # builder_sprint_interval: int       = 3600
    # builder_rest_seconds: int          = 900
    # builder_max_sprints: int           = 8
    # builder_wall_limit: int            = 28800
    # builder_release_threshold: int     = 5
    # builder_branch_prefix: str         = "self/"
    # builder_cb_threshold: int          = 4
    # builder_worktree_path: str         = "/acorn-warden-wt"
    # builder_ollama_url: str            = "http://acorn-api-relay:9000"

    # -- CORS ---------------------------------------------------------------------
    cors_origins: list[str] = Field(
        default=["http://localhost:8501", "http://localhost:3000"])

    # -- Feature flags ------------------------------------------------------------
    kernel_extraction_enabled: bool   = True
    judge_required: bool              = True
    meta_agent_enabled: bool          = True
    ui_evolution_enabled: bool        = False
    concurrent_problems_enabled: bool = False

    def model_for_role(self, role: str) -> str:
        """Return the model for a given agent role, with env override support."""
        import os
        role_overrides = {
            "orchestrator": "ORCHESTRATOR_MODEL",
            "research-analyst": "RESEARCH_MODEL",
            "synthesis-agent": "SYNTHESIS_MODEL",
            "judge-agent": "JUDGE_MODEL",
        }
        env_key = role_overrides.get(role)
        if env_key:
            override = os.environ.get(env_key)
            if override:
                return override
        role_models = {
            "orchestrator": self.coder_model,
            "research-analyst": self.analysis_model,
            "synthesis-agent": self.coder_model,
            "domain-specialist": self.analysis_model,
            "validator": self.analysis_model,
            "judge-agent": self.coder_model,
            "kernel-extractor": self.analysis_model,
            "interface-agent": self.coder_model,
            "calibration-agent": self.coder_model,
            "data-scientist": self.analysis_model,
            "meta-agent": self.reasoning_model,
            "software-architect": self.reasoning_model,
        }
        return role_models.get(role, self.coder_model)

    @model_validator(mode="after")
    def validate_escalation_config(self) -> "AcornSettings":
        if self.stall_detection_enabled and not self.anthropic_api_key_real:
            # Not a hard error -- proxy will log and fall back to local
            import warnings
            warnings.warn(
                "STALL_DETECTION_ENABLED=true but ANTHROPIC_API_KEY_REAL is empty. "
                "Escalation will be attempted and silently fall back to Ollama response.",
                stacklevel=2)
        return self

    @model_validator(mode="after")
    def validate_resource_caps(self) -> "AcornSettings":
        if self.acorn_mode == AcornMode.MINI and self.max_agents_per_problem > 4:
            import warnings
            warnings.warn(
                f"ACORN_MODE=mini but MAX_AGENTS_PER_PROBLEM={self.max_agents_per_problem}. "
                "Mini profile recommends <= 4 agents per problem due to memory constraints.",
                stacklevel=2)
        return self

    @model_validator(mode="after")
    def apply_mode_defaults(self) -> "AcornSettings":
        """Apply platform-specific defaults when values are at their generic defaults."""
        if self.acorn_mode == AcornMode.MINI:
            if self.max_concurrent_problems == 3:
                object.__setattr__(self, "max_concurrent_problems", 1)
        return self


# Singleton -- imported by all modules
settings = AcornSettings()
