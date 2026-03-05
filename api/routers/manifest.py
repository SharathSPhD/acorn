"""Manifest API: desired vs actual state and gaps."""
__pattern__ = "Repository"

from pathlib import Path

from fastapi import APIRouter

from api.config import settings
from api.services.manifest_engine import ManifestEngine

router = APIRouter(prefix="/api/manifest", tags=["manifest"])


def _resolve_manifest_path() -> Path:
    candidates = [
        Path(settings.acorn_root) / "manifest_domains.json",
        Path("/app") / "manifest_domains.json",
        Path(__file__).resolve().parents[2] / "manifest_domains.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


_MANIFEST_PATH = _resolve_manifest_path()


@router.get("/status")
async def manifest_status() -> dict:
    """Return desired vs actual state from manifest engine."""
    engine = ManifestEngine(str(_MANIFEST_PATH))
    return await engine.perceive()


@router.get("/deltas")
async def manifest_deltas() -> list[dict]:
    """Return current gaps between desired and actual state."""
    engine = ManifestEngine(str(_MANIFEST_PATH))
    return await engine.reconcile()
