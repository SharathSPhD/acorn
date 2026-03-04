"""AgentFactory implementations for launching harness containers."""
__pattern__ = "Factory"

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from uuid import uuid4

from api.config import OAKMode, settings


class ResourceCapExceededError(Exception):
    """Raised when Docker refuses to start a container."""


@dataclass
class AgentSpec:
    """Container spec produced by AgentFactory.create()."""
    agent_id: str
    role: str
    problem_uuid: str
    model: str = "qwen3-coder"
    harness_image: str = "oak/harness:latest"
    resource_limits: dict[str, str] = field(
        default_factory=lambda: {"memory": "4g", "cpus": "2.0"}
    )
    network: str = "oak_oak-net"
    workspace_path: str = ""
    task_id: str = ""
    extra_env: dict[str, str] = field(default_factory=dict)


class AgentFactory(ABC):
    """Abstract factory for agent session creation."""

    @abstractmethod
    def create(self, role: str, problem_uuid: str, **kwargs: str) -> AgentSpec:
        """Produce an agent spec; does not launch the container."""

    @abstractmethod
    async def launch(self, spec: AgentSpec) -> str:
        """Launch the harness container; return container ID."""


class DGXAgentFactory(AgentFactory):
    """Concrete factory for DGX Spark profile."""

    def create(self, role: str, problem_uuid: str, **kwargs: str) -> AgentSpec:
        model = settings.model_for_role(role)
        spec = AgentSpec(
            agent_id=kwargs.get("container_name", str(uuid4())),
            role=role,
            problem_uuid=problem_uuid,
            model=model,
        )
        if "task_id" in kwargs:
            spec.task_id = kwargs["task_id"]
        return spec

    async def launch(self, spec: AgentSpec) -> str:
        env_pairs: list[str] = []

        base_env = {
            "ANTHROPIC_BASE_URL": "http://oak-api-proxy:9000",
            "ANTHROPIC_AUTH_TOKEN": "ollama",
            "ANTHROPIC_API_KEY": "ollama",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            "OAK_PROBLEM_UUID": spec.problem_uuid,
            "OAK_AGENT_ID": spec.agent_id,
            "OAK_ROLE": spec.role,
            "OAK_API_URL": "http://oak-api:8000",
            "OAK_MODEL": spec.model,
            "REDIS_URL": settings.redis_url,
            "DATABASE_URL": settings.database_url,
        }
        if spec.task_id:
            base_env["OAK_TASK_ID"] = spec.task_id

        base_env.update(spec.extra_env)

        for k, v in base_env.items():
            env_pairs.extend(["-e", f"{k}={v}"])

        cmd: list[str] = [
            "docker", "run", "-d",
            "--name", spec.agent_id,
            "--network", spec.network,
            "--memory", spec.resource_limits.get("memory", "4g"),
            "--cpus", spec.resource_limits.get("cpus", "2.0"),
            *env_pairs,
        ]

        if spec.workspace_path:
            cmd.extend(["-v", f"{spec.workspace_path}:/workspace"])

        cmd.append(spec.harness_image)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise ResourceCapExceededError(stderr.decode().strip())
        return stdout.decode().strip()


class MiniAgentFactory(AgentFactory):
    """Concrete factory for Mac Mini M4 profile. Phase 4."""

    def create(self, role: str, problem_uuid: str, **kwargs: str) -> AgentSpec:
        raise NotImplementedError("Phase 4")

    async def launch(self, spec: AgentSpec) -> str:
        raise NotImplementedError("Phase 4")


class CloudAgentFactory(AgentFactory):
    """Concrete factory for cloud GPU profile. Phase 5."""

    def create(self, role: str, problem_uuid: str, **kwargs: str) -> AgentSpec:
        raise NotImplementedError("Phase 5")

    async def launch(self, spec: AgentSpec) -> str:
        raise NotImplementedError("Phase 5")


def get_agent_factory() -> AgentFactory:
    """Return the appropriate factory for the current OAK_MODE."""
    if settings.oak_mode == OAKMode.MINI:
        return MiniAgentFactory()
    if settings.oak_mode == OAKMode.CLOUD:
        return CloudAgentFactory()
    return DGXAgentFactory()
