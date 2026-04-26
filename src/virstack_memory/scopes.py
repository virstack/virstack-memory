"""Multi-tenant scope builder for Graphiti group IDs.

The :class:`MemoryScope` class implements a fluent builder pattern that
constructs hierarchical ``group_id`` strings like
``proj_1_ws_A_agt_X_cust_999`` and exposes the scoped CRUD operations
(``add_messages``, ``search``, ``delete``, etc.) that target the correct
bucket in the Neo4j graph.

Hierarchy::

    Project ─► Workspace ─► Agent ─► Customer
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from virstack_memory.models import (
    FactResult,
    GetMemoryResponse,
    Message,
    Result,
    SearchResults,
)

if TYPE_CHECKING:
    from virstack_memory.client import GraphitiClient


# Compact prefix map for building group_id strings
_PREFIX_MAP: dict[str, str] = {
    "project": "proj",
    "workspace": "ws",
    "agent": "agt",
    "customer": "cust",
}


class MemoryScope:
    """Represents a specific multi-tenant memory bucket.

    Instances are created via :meth:`GraphitiClient.project` and then
    chained with ``.workspace()``, ``.agent()``, and ``.customer()`` to
    narrow the scope.  The resulting :attr:`active_group_id` is used as
    the ``group_id`` parameter for all Graphiti API calls made through
    this scope.

    Args:
        client: The parent :class:`GraphitiClient` used for HTTP calls.
        scope_name: Human-readable scope level name (``project``, ``workspace``, etc.).
        scope_id: The unique identifier for this scope level.
        parent: Optional parent scope for building the full path.
    """

    __slots__ = ("_client", "parent", "scope_id", "scope_name")

    def __init__(
        self,
        client: GraphitiClient,
        scope_name: str,
        scope_id: str,
        parent: MemoryScope | None = None,
    ) -> None:
        self._client = client
        self.scope_name = scope_name
        self.scope_id = scope_id
        self.parent = parent

    # ── Hierarchy builders ──────────────────────────────────────────

    def workspace(self, workspace_id: str) -> MemoryScope:
        """Narrow scope to a specific workspace within the current project."""
        return MemoryScope(self._client, "workspace", workspace_id, parent=self)

    def agent(self, agent_id: str) -> MemoryScope:
        """Narrow scope to a specific agent within the current workspace."""
        return MemoryScope(self._client, "agent", agent_id, parent=self)

    def customer(self, customer_id: str) -> MemoryScope:
        """Narrow scope to a specific customer within the current agent."""
        return MemoryScope(self._client, "customer", customer_id, parent=self)

    # ── Identifiers ─────────────────────────────────────────────────

    @property
    def active_group_id(self) -> str:
        """Build the full database bucket ID path for this scope.

        Walks the parent chain upward and joins each level's prefix and
        ID with underscores.

        Examples::

            client.project("1").active_group_id
            # => "proj_1"

            client.project("1").workspace("A").agent("X").customer("999").active_group_id
            # => "proj_1_ws_A_agt_X_cust_999"
        """
        parts: list[str] = []
        curr: MemoryScope | None = self

        while curr is not None:
            prefix = _PREFIX_MAP.get(curr.scope_name, curr.scope_name)
            parts.append(f"{prefix}_{curr.scope_id}")
            curr = curr.parent

        # Parts were collected child-first; reverse to get root-first
        parts.reverse()
        return "_".join(parts)

    @property
    def cascading_group_ids(self) -> list[str]:
        """Return this scope's path **plus** all parent paths.

        This produces the array passed to ``POST /search`` so the query
        can fan out across multiple isolation levels (e.g. customer-level
        facts *and* workspace-level policies).

        Examples::

            client.project("1").workspace("A").agent("X").customer("999").cascading_group_ids
            # => [
            #     "proj_1",
            #     "proj_1_ws_A",
            #     "proj_1_ws_A_agt_X",
            #     "proj_1_ws_A_agt_X_cust_999",
            # ]
        """
        # Collect all ancestor scopes (including self)
        ancestors: list[MemoryScope] = []
        curr: MemoryScope | None = self
        while curr is not None:
            ancestors.append(curr)
            curr = curr.parent
        ancestors.reverse()  # root-first

        # Build the cumulative path for each ancestor
        ids: list[str] = []
        for scope in ancestors:
            ids.append(scope.active_group_id)
        return ids

    # ── Core CRUD operations ────────────────────────────────────────

    async def add_messages(self, messages: list[Message]) -> Result:
        """``POST /messages`` — Ingest conversation messages into this scope.

        The server queues messages asynchronously and returns ``202 Accepted``.

        Args:
            messages: List of :class:`Message` objects to ingest.

        Returns:
            A :class:`Result` confirming the messages were queued.
        """
        payload = {
            "group_id": self.active_group_id,
            "messages": [m.model_dump(mode="json", exclude_none=True) for m in messages],
        }
        data = await self._client._post("/messages", payload)
        return Result.model_validate(data)

    async def add_entity_node(self, uuid: str, name: str, summary: str = "") -> dict[str, Any]:
        """``POST /entity-node`` — Create a manual entity node in this scope.

        Args:
            uuid: Client-generated UUID for the entity.
            name: Human-readable entity name.
            summary: Optional summary text for the entity.

        Returns:
            The created entity node as a dict (server returns 201).
        """
        payload = {
            "uuid": uuid,
            "group_id": self.active_group_id,
            "name": name,
            "summary": summary,
        }
        return await self._client._post("/entity-node", payload)

    async def search(
        self,
        query: str,
        *,
        max_facts: int = 10,
        include_parents: bool = True,
    ) -> list[FactResult]:
        """``POST /search`` — Search for facts in the knowledge graph.

        Args:
            query: Natural-language search query.
            max_facts: Maximum number of facts to return.
            include_parents: If ``True``, search across all ancestor scopes
                (cascading). If ``False``, search only this exact scope.

        Returns:
            A list of :class:`FactResult` objects matching the query.
        """
        target_ids = self.cascading_group_ids if include_parents else [self.active_group_id]
        payload = {
            "query": query,
            "group_ids": target_ids,
            "max_facts": max_facts,
        }
        data = await self._client._post("/search", payload)
        return SearchResults.model_validate(data).facts

    async def get_memory(
        self,
        messages: list[Message],
        *,
        max_facts: int = 10,
        center_node_uuid: str | None = None,
    ) -> list[FactResult]:
        """``POST /get-memory`` — Retrieve contextual memory from messages.

        This endpoint composes a search query from the provided messages
        and returns relevant facts from this scope.

        Args:
            messages: Conversation messages to derive the query from.
            max_facts: Maximum number of facts to return.
            center_node_uuid: Optional UUID to center the graph retrieval on.

        Returns:
            A list of :class:`FactResult` objects.
        """
        payload = {
            "group_id": self.active_group_id,
            "max_facts": max_facts,
            "center_node_uuid": center_node_uuid,
            "messages": [m.model_dump(mode="json", exclude_none=True) for m in messages],
        }
        data = await self._client._post("/get-memory", payload)
        return GetMemoryResponse.model_validate(data).facts

    async def get_episodes(self, *, last_n: int = 10) -> list[dict[str, Any]]:
        """``GET /episodes/{group_id}`` — Retrieve recent episodes.

        Args:
            last_n: Number of most recent episodes to fetch.

        Returns:
            A list of episode dicts from the server.
        """
        return await self._client._get(
            f"/episodes/{self.active_group_id}",
            params={"last_n": last_n},
        )

    async def delete(self) -> Result:
        """``DELETE /group/{group_id}`` — Delete all data in this scope.

        .. warning::
            This permanently removes all nodes and edges scoped to this
            exact ``group_id``. Parent and sibling scopes are unaffected.

        Returns:
            A :class:`Result` confirming the deletion.
        """
        data = await self._client._delete(f"/group/{self.active_group_id}")
        return Result.model_validate(data)

    # ── Representation ──────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"MemoryScope(group_id={self.active_group_id!r})"
