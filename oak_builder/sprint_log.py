"""Sprint log — records sprint results and manages release tagging.

Maintains per-domain judge score baselines for the Tier 2 functional
gate and tracks "stories" (skills + commits) toward the release threshold.
"""
from __future__ import annotations

__pattern__ = "Repository"

import json
import logging
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger("oak.builder.sprint_log")


@dataclass
class SprintResult:
    sprint_number: int
    started_at: str
    finished_at: str
    problems_submitted: int = 0
    problems_passed: int = 0
    problems_failed: int = 0
    skills_ingested: int = 0
    changes_committed: bool = False
    commit_branch: str = ""
    circuit_breaker_state: str = "closed"
    domain_results: dict = field(default_factory=dict)


class SprintLog:
    """Persistent log of sprint results stored as JSON."""

    def __init__(
        self, log_path: str = "/workspaces/builder/sprint_log.json",
        release_threshold: int = 5,
    ) -> None:
        self.log_path = Path(log_path)
        self.release_threshold = release_threshold
        self._data = self._load()

    def _load(self) -> dict:
        if self.log_path.exists():
            try:
                return json.loads(self.log_path.read_text())
            except json.JSONDecodeError:
                logger.warning("Corrupt sprint log, starting fresh")
        return {
            "sprints": [],
            "total_skills": 0,
            "total_commits": 0,
            "stories_since_release": 0,
            "release_count": 0,
            "domain_baselines": {},
        }

    def _save(self) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.write_text(json.dumps(self._data, indent=2))

    def record_sprint(self, result: SprintResult) -> None:
        self._data["sprints"].append(asdict(result))
        self._data["total_skills"] += result.skills_ingested
        if result.changes_committed:
            self._data["total_commits"] += 1

        stories = result.skills_ingested + (1 if result.changes_committed else 0)
        self._data["stories_since_release"] += stories

        for domain_id, domain_result in result.domain_results.items():
            score = domain_result.get("judge_score")
            if score is not None:
                self._data["domain_baselines"][domain_id] = score

        self._save()
        logger.info(
            "Sprint %d logged: %d problems, %d skills, %d stories toward release",
            result.sprint_number,
            result.problems_submitted,
            result.skills_ingested,
            self._data["stories_since_release"],
        )

    def should_release(self) -> bool:
        return self._data["stories_since_release"] >= self.release_threshold

    def create_release(self, repo_path: str) -> str | None:
        """Tag a release and reset the story counter."""
        release_num = self._data["release_count"] + 1
        tag = f"self-v{release_num}"

        try:
            subprocess.run(
                ["git", "-C", repo_path, "tag", tag, "-m",
                 f"Self-build release {tag}: "
                 f"{self._data['total_skills']} skills, "
                 f"{self._data['total_commits']} commits"],
                capture_output=True, text=True, timeout=10,
                check=True,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            logger.error("Failed to tag release %s: %s", tag, exc)
            return None

        self._data["release_count"] = release_num
        self._data["stories_since_release"] = 0
        self._save()
        logger.info("Release %s tagged", tag)
        return tag

    def get_domain_baseline(self, domain_id: str) -> float | None:
        return self._data["domain_baselines"].get(domain_id)

    @property
    def sprint_count(self) -> int:
        return len(self._data["sprints"])

    @property
    def stories_since_release(self) -> int:
        return self._data["stories_since_release"]

    def to_dict(self) -> dict:
        return {
            "sprint_count": self.sprint_count,
            "total_skills": self._data["total_skills"],
            "total_commits": self._data["total_commits"],
            "stories_since_release": self._data["stories_since_release"],
            "release_count": self._data["release_count"],
            "domain_baselines": self._data["domain_baselines"],
        }

    def recent_sprints(self, n: int = 10) -> list[dict]:
        return self._data["sprints"][-n:]
