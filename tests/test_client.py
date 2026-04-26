"""Unit tests for MemoryClient HTTP operations."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from virstack_memory.client import MemoryClient
from virstack_memory.exceptions import (
    MemoryAPIError,
    MemoryConnectionError,
    MemoryValidationError,
)
from virstack_memory.models import Message
from virstack_memory.scopes import MemoryScope

# ── Client lifecycle ────────────────────────────────────────────────


class TestClientLifecycle:
    """Test client construction, context manager, and close."""

    def test_base_url_trailing_slash_stripped(self) -> None:
        c = MemoryClient("http://localhost:8000/")
        assert c.base_url == "http://localhost:8000"

    def test_project_returns_memory_scope(self, client: MemoryClient) -> None:
        scope = client.project("test")
        assert isinstance(scope, MemoryScope)

    async def test_async_context_manager(self, mock_http: AsyncMock) -> None:
        async with MemoryClient("http://localhost:8000") as c:
            c.http = mock_http
            assert c is not None
        # aclose should have been called on exit
        mock_http.aclose.assert_awaited_once()

    async def test_close_calls_aclose(self, client: MemoryClient, mock_http: AsyncMock) -> None:
        await client.close()
        mock_http.aclose.assert_awaited_once()


# ── Healthcheck ─────────────────────────────────────────────────────


class TestHealthcheck:
    """Test the GET /healthcheck endpoint wrapper."""

    async def test_healthy(self, client: MemoryClient, mock_http: AsyncMock) -> None:
        response = MagicMock()
        response.status_code = 200
        mock_http.get.return_value = response

        assert await client.healthcheck() is True
        mock_http.get.assert_awaited_with("/healthcheck")

    async def test_unhealthy(self, client: MemoryClient, mock_http: AsyncMock) -> None:
        response = MagicMock()
        response.status_code = 503
        mock_http.get.return_value = response

        assert await client.healthcheck() is False

    async def test_connection_error_returns_false(
        self, client: MemoryClient, mock_http: AsyncMock
    ) -> None:
        import httpx

        mock_http.get.side_effect = httpx.ConnectError("refused")
        assert await client.healthcheck() is False


# ── Error handling ──────────────────────────────────────────────────


class TestErrorHandling:
    """Test that HTTP errors are mapped to SDK exceptions."""

    async def test_422_raises_validation_error(
        self, client: MemoryClient, mock_http: AsyncMock
    ) -> None:
        response = MagicMock()
        response.status_code = 422
        response.is_success = False
        response.text = '{"detail": "bad field"}'
        mock_http.post.return_value = response

        with pytest.raises(MemoryValidationError) as exc_info:
            await client._post("/messages", {})
        assert exc_info.value.status_code == 422

    async def test_500_raises_api_error(self, client: MemoryClient, mock_http: AsyncMock) -> None:
        response = MagicMock()
        response.status_code = 500
        response.is_success = False
        response.text = "Internal Server Error"
        mock_http.post.return_value = response

        with pytest.raises(MemoryAPIError) as exc_info:
            await client._post("/messages", {})
        assert exc_info.value.status_code == 500

    async def test_connection_error_wraps_httpx(
        self, client: MemoryClient, mock_http: AsyncMock
    ) -> None:
        import httpx

        mock_http.post.side_effect = httpx.ConnectError("refused")

        with pytest.raises(MemoryConnectionError):
            await client._post("/messages", {})

    async def test_timeout_wraps_httpx(self, client: MemoryClient, mock_http: AsyncMock) -> None:
        import httpx

        mock_http.delete.side_effect = httpx.TimeoutException("timed out")

        with pytest.raises(MemoryConnectionError):
            await client._delete("/group/test")


# ── Scoped operations payload tests ─────────────────────────────────


class TestScopedOperations:
    """Verify that scoped operations send the correct payloads."""

    async def test_add_messages_payload(
        self, full_scope: MemoryScope, mock_http: AsyncMock
    ) -> None:
        msgs = [Message(content="Hello", role_type="user")]

        response = MagicMock()
        response.status_code = 202
        response.is_success = True
        response.content = b'{"message": "Messages added to processing queue", "success": true}'
        response.json.return_value = {
            "message": "Messages added to processing queue",
            "success": True,
        }
        mock_http.post.return_value = response

        result = await full_scope.add_messages(msgs)
        assert result.success is True

        # Verify the POST was called with correct path and payload shape
        call_args = mock_http.post.call_args
        assert call_args[0][0] == "/messages"
        payload = call_args[1]["json"]
        assert payload["group_id"] == "proj_1_ws_A_agt_X_cust_999"
        assert len(payload["messages"]) == 1
        assert payload["messages"][0]["content"] == "Hello"

    async def test_search_with_cascading(
        self, full_scope: MemoryScope, mock_http: AsyncMock
    ) -> None:
        response = MagicMock()
        response.status_code = 200
        response.is_success = True
        response.content = b'{"facts": []}'
        response.json.return_value = {"facts": []}
        mock_http.post.return_value = response

        facts = await full_scope.search("test query", include_parents=True)
        assert facts == []

        call_args = mock_http.post.call_args
        assert call_args[0][0] == "/search"
        payload = call_args[1]["json"]
        assert payload["group_ids"] == [
            "proj_1",
            "proj_1_ws_A",
            "proj_1_ws_A_agt_X",
            "proj_1_ws_A_agt_X_cust_999",
        ]

    async def test_search_without_cascading(
        self, full_scope: MemoryScope, mock_http: AsyncMock
    ) -> None:
        response = MagicMock()
        response.status_code = 200
        response.is_success = True
        response.content = b'{"facts": []}'
        response.json.return_value = {"facts": []}
        mock_http.post.return_value = response

        await full_scope.search("test", include_parents=False)

        payload = mock_http.post.call_args[1]["json"]
        assert payload["group_ids"] == ["proj_1_ws_A_agt_X_cust_999"]

    async def test_delete_sends_correct_path(
        self, full_scope: MemoryScope, mock_http: AsyncMock
    ) -> None:
        response = MagicMock()
        response.status_code = 200
        response.is_success = True
        response.content = b'{"message": "Group deleted", "success": true}'
        response.json.return_value = {"message": "Group deleted", "success": True}
        mock_http.delete.return_value = response

        result = await full_scope.delete()
        assert result.success is True
        mock_http.delete.assert_awaited_with("/group/proj_1_ws_A_agt_X_cust_999")

    async def test_add_entity_node_payload(
        self, full_scope: MemoryScope, mock_http: AsyncMock
    ) -> None:
        response = MagicMock()
        response.status_code = 201
        response.is_success = True
        response.content = b'{"uuid": "abc", "name": "Test Entity"}'
        response.json.return_value = {"uuid": "abc", "name": "Test Entity"}
        mock_http.post.return_value = response

        result = await full_scope.add_entity_node(uuid="abc", name="Test Entity", summary="A test")
        assert result["uuid"] == "abc"

        payload = mock_http.post.call_args[1]["json"]
        assert payload["group_id"] == "proj_1_ws_A_agt_X_cust_999"
        assert payload["name"] == "Test Entity"
        assert payload["summary"] == "A test"
