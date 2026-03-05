import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime
from fastapi.testclient import TestClient
from api.main import app
from memory.interfaces import PromotionThresholdNotMetError


client = TestClient(app)


def test_kernels_router__list_with_query__returns_200_and_kernels():
    """GET /api/kernels?query=... returns matching kernels."""
    kernel_id = uuid4()
    mock_kernel = MagicMock()
    mock_kernel.id = kernel_id
    mock_kernel.name = "etl-pipeline"
    mock_kernel.category = "etl"
    mock_kernel.description = "ETL kernel"
    mock_kernel.trigger_keywords = ["pipeline"]
    mock_kernel.status = "permanent"
    mock_kernel.use_count = 5
    mock_kernel.verified_on_problems = []
    mock_kernel.filesystem_path = "/kernels/etl.md"

    with patch("api.routers.kernels.PostgreSQLKernelRepository") as mock_repo_class:
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.find_by_keywords = AsyncMock(return_value=[mock_kernel])

        response = client.get("/api/kernels?query=pipeline&top_k=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "etl-pipeline"
        assert data[0]["category"] == "etl"


def test_kernels_router__list_no_query__returns_200():
    """GET /api/kernels without query returns all permanent kernels."""
    mock_row = MagicMock()
    mock_row.__getitem__ = lambda self, key: {
        "id": uuid4(),
        "name": "test-kernel",
        "category": "etl",
        "description": "Test kernel",
        "trigger_keywords": ["test"],
        "embedding": None,
        "status": "permanent",
        "use_count": 3,
        "verified_on_problems": [],
        "filesystem_path": "/kernels/test.md",
        "deprecated_reason": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }[key]

    with patch("asyncpg.connect") as mock_connect:
        mock_conn = AsyncMock()
        mock_connect.return_value = mock_conn
        mock_conn.fetch.return_value = [mock_row]

        response = client.get("/api/kernels")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "test-kernel"


def test_kernels_router__promote__threshold_not_met__returns_409():
    """POST /api/kernels/{kernel_id}/promote returns 409 when threshold not met."""
    kernel_id = uuid4()

    with patch("api.routers.kernels.PostgreSQLKernelRepository") as mock_repo_class:
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.promote = AsyncMock(side_effect=PromotionThresholdNotMetError("Need 2, have 1"))

        response = client.post(f"/api/kernels/{kernel_id}/promote")

        assert response.status_code == 409
        assert "Need 2, have 1" in response.json()["detail"]


def test_kernels_router__promote__not_found__returns_404():
    """POST /api/kernels/{kernel_id}/promote returns 404 when kernel not found."""
    kernel_id = uuid4()

    with patch("api.routers.kernels.PostgreSQLKernelRepository") as mock_repo_class:
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.promote = AsyncMock(side_effect=ValueError(f"Kernel {kernel_id} not found"))

        response = client.post(f"/api/kernels/{kernel_id}/promote")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
