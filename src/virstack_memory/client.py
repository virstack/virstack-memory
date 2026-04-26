"""Base HTTP client for the Memory FastAPI server.

Provides :class:`MemoryClient`, a thin async wrapper around
``httpx.AsyncClient`` that handles global endpoints (``/healthcheck``,
``/clear``) and acts as the entry-point for the scope chain via
:meth:`MemoryClient.project`.
"""

from __future__ import annotations

from typing import Any

import httpx

from virstack_memory.exceptions import (
    MemoryAPIError,
    MemoryConnectionError,
    MemoryValidationError,
)
from virstack_memory.models import Result
from virstack_memory.scopes import MemoryScope


class MemoryClient:
    """Async client for the Memory server.

    Args:
        base_url: Root URL of the Memory server (e.g. ``http://localhost:8000``).
        timeout: HTTP request timeout in seconds. Defaults to ``45.0``.

    Usage::

        async with MemoryClient("http://localhost:8000") as client:
            ok = await client.healthcheck()
            scope = client.project("proj_1").workspace("ws_A")
    """

    def __init__(self, base_url: str, *, timeout: float = 45.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.http = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)

    # ── Async context manager ───────────────────────────────────────

    async def __aenter__(self) -> MemoryClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    # ── Scope chain entry-point ─────────────────────────────────────

    def project(self, project_id: str) -> MemoryScope:
        """Start a scope chain at the **Project** level.

        Args:
            project_id: Unique identifier for the project.

        Returns:
            A :class:`MemoryScope` that can be further chained with
            ``.workspace()``, ``.agent()``, and ``.customer()``.
        """
        return MemoryScope(self, "project", project_id)

    # ── Global endpoints ────────────────────────────────────────────

    async def healthcheck(self) -> bool:
        """``GET /healthcheck`` — Returns ``True`` if the server is healthy."""
        try:
            res = await self.http.get("/healthcheck")
            return res.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def clear(self) -> Result:
        """``POST /clear`` — Wipes **all** data from the Neo4j graph.

        .. warning::
            This is a destructive operation that removes every node and
            edge across all tenants. Use with extreme caution.

        Returns:
            A :class:`Result` with ``success=True`` on success.
        """
        data = await self._post("/clear", {})
        return Result.model_validate(data)

    # ── Internal HTTP helpers ───────────────────────────────────────

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Send a POST request and return the parsed JSON body.

        Raises:
            MemoryConnectionError: On network-level failures.
            MemoryValidationError: On 422 responses.
            MemoryAPIError: On any other non-2xx status.
        """
        try:
            res = await self.http.post(path, json=payload)
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise MemoryConnectionError(str(exc)) from exc

        self._raise_for_status(res)
        return res.json() if res.content else {}

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Send a GET request and return the parsed JSON body."""
        try:
            res = await self.http.get(path, params=params)
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise MemoryConnectionError(str(exc)) from exc

        self._raise_for_status(res)
        return res.json() if res.content else {}

    async def _delete(self, path: str) -> dict[str, Any]:
        """Send a DELETE request and return the parsed JSON body."""
        try:
            res = await self.http.delete(path)
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise MemoryConnectionError(str(exc)) from exc

        self._raise_for_status(res)
        return res.json() if res.content else {}

    # ── Response validation ─────────────────────────────────────────

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        """Translate non-2xx HTTP responses into SDK exceptions."""
        if response.is_success:
            return

        detail = response.text
        if response.status_code == 422:
            raise MemoryValidationError(detail)
        raise MemoryAPIError(response.status_code, detail)

    # ── Lifecycle ───────────────────────────────────────────────────

    async def close(self) -> None:
        """Close the underlying ``httpx.AsyncClient`` and release connections."""
        await self.http.aclose()
