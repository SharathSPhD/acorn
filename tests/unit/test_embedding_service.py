"""Tests for api.services.embedding.EmbeddingService."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def _mock_settings() -> MagicMock:
    s = MagicMock()
    s.ollama_base_url = "http://test-ollama:11434"
    s.embed_model = "nomic-embed-text"
    s.embed_dim = 768
    return s


@pytest.mark.asyncio
async def test_embed__returns_vector(_mock_settings: MagicMock) -> None:
    from api.services.embedding import EmbeddingService

    svc = EmbeddingService(settings=_mock_settings)
    fake_vec = [0.1] * 768
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"embedding": fake_vec}
    mock_resp.raise_for_status = MagicMock()

    with patch("api.services.embedding.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await svc.embed("test query")
        assert len(result) == 768
        mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_embed_batch__returns_multiple(_mock_settings: MagicMock) -> None:
    from api.services.embedding import EmbeddingService

    svc = EmbeddingService(settings=_mock_settings)
    fake_vec = [0.1] * 768
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"embedding": fake_vec}
    mock_resp.raise_for_status = MagicMock()

    with patch("api.services.embedding.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        results = await svc.embed_batch(["a", "b", "c"])
        assert len(results) == 3
        assert all(len(v) == 768 for v in results)


def test_dimension(_mock_settings: MagicMock) -> None:
    from api.services.embedding import EmbeddingService

    svc = EmbeddingService(settings=_mock_settings)
    assert svc.dimension == 768
