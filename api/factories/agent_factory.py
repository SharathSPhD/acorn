__pattern__ = "Factory"

from abc import ABC, abstractmethod
from typing import Protocol


class ResourceCapExceeded(Exception):
    pass


class AgentSpec(Protocol):
    agent_id: str
    role: str
    harness_image: str
    resource_limits: dict


class AgentFactory(ABC):
    """Abstract factory for agent session creation.
    Each platform profile provides a concrete subclass."""

    @abstractmethod
    def create(self, role: str, problem_uuid: str) -> AgentSpec:
        """Produce an agent spec; does not launch the container."""
        ...

    @abstractmethod
    def launch(self, spec: AgentSpec) -> str:
        """Launch the harness container; return container ID."""
        ...


class DGXAgentFactory(AgentFactory):
    """Concrete factory for DGX Spark profile.
    GPU passthrough, full 70B model set, high MAX_AGENTS."""

    def create(self, role: str, problem_uuid: str) -> AgentSpec:
        raise NotImplementedError("Phase 1")

    def launch(self, spec: AgentSpec) -> str:
        raise NotImplementedError("Phase 1")


class MiniAgentFactory(AgentFactory):
    """Concrete factory for Mac Mini M4 profile.
    Metal backend, smaller models, conservative resource limits."""

    def create(self, role: str, problem_uuid: str) -> AgentSpec:
        raise NotImplementedError("Phase 4")

    def launch(self, spec: AgentSpec) -> str:
        raise NotImplementedError("Phase 4")


class CloudAgentFactory(AgentFactory):
    """Concrete factory for cloud GPU profile.
    vLLM backend, Kubernetes job creation, horizontal scaling."""

    def create(self, role: str, problem_uuid: str) -> AgentSpec:
        raise NotImplementedError("Phase 5")

    def launch(self, spec: AgentSpec) -> str:
        raise NotImplementedError("Phase 5")
