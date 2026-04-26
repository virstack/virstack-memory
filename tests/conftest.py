"""Shared pytest fixtures for the virstack-graphiti test suite."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from virstack_memory.client import GraphitiClient
from virstack_memory.scopes import MemoryScope


@pytest.fixture
def mock_http() -> AsyncMock:
    """A mocked ``httpx.AsyncClient`` with sensible defaults."""
    http = AsyncMock()

    # Default: POST returns 200 with an empty JSON body
    response = MagicMock()
    response.status_code = 200
    response.is_success = True
    response.content = b'{"message": "ok", "success": true}'
    response.json.return_value = {"message": "ok", "success": True}
    response.text = '{"message": "ok", "success": true}'

    http.post.return_value = response
    http.get.return_value = response
    http.delete.return_value = response
    http.aclose.return_value = None

    return http


@pytest.fixture
def client(mock_http: AsyncMock) -> GraphitiClient:
    """A :class:`GraphitiClient` with its HTTP transport replaced by a mock."""
    c = GraphitiClient("http://test:8000")
    c.http = mock_http
    return c


@pytest.fixture
def full_scope(client: GraphitiClient) -> MemoryScope:
    """A fully-chained scope: project → workspace → agent → customer."""
    return client.project("1").workspace("A").agent("X").customer("999")


@pytest.fixture
def project_scope(client: GraphitiClient) -> MemoryScope:
    """A project-level scope."""
    return client.project("1")


@pytest.fixture
def workspace_scope(client: GraphitiClient) -> MemoryScope:
    """A project + workspace scope."""
    return client.project("1").workspace("A")
