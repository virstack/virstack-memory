"""Integration tests against a live Memory server.

These tests require a running Memory server at ``http://localhost:8000``.
They are skipped automatically if the server is unreachable.

Run manually::

    uv run pytest tests/test_integration.py -v
"""

from __future__ import annotations

import uuid

import httpx
import pytest

from virstack_memory.client import MemoryClient
from virstack_memory.models import Message


def _server_is_up() -> bool:
    """Synchronous check if the Memory server is reachable."""
    try:
        r = httpx.get("http://localhost:8000/healthcheck", timeout=3.0)
        return r.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


# Skip the entire module if the server is not reachable
pytestmark = pytest.mark.skipif(
    not _server_is_up(),
    reason="Memory server not running at localhost:8000",
)


@pytest.fixture
async def client():
    """Provide a live MemoryClient and close it after the test."""
    async with MemoryClient("http://localhost:8000") as c:
        yield c


@pytest.fixture
def test_group_id() -> str:
    """Generate a unique group_id for test isolation."""
    return f"proj_test_{uuid.uuid4().hex[:8]}"


class TestLiveHealthcheck:
    async def test_server_is_healthy(self, client: MemoryClient) -> None:
        assert await client.healthcheck() is True


class TestLiveMessages:
    async def test_add_and_search(self, client: MemoryClient, test_group_id: str) -> None:
        scope = client.project(f"test_{test_group_id}")

        # Ingest a message
        result = await scope.add_messages(
            [
                Message(
                    content="The customer prefers email communication.",
                    role_type="assistant",
                    role="Agent",
                ),
            ]
        )
        assert result.success is True

        # Note: The server processes messages asynchronously, so an
        # immediate search may not find the ingested data. This test
        # only verifies the request/response cycle is correct.
        facts = await scope.search("customer communication preference", max_facts=5)
        # facts may be empty if the async worker hasn't processed yet
        assert isinstance(facts, list)


class TestLiveDelete:
    async def test_delete_group(self, client: MemoryClient, test_group_id: str) -> None:
        scope = client.project(f"test_{test_group_id}")
        result = await scope.delete()
        assert result.success is True
