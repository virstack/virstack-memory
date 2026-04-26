"""Virstack Graphiti SDK — Python client for the Graphiti memory server.

Quick start::

    from virstack_memory import GraphitiClient, Message

    async with GraphitiClient("http://localhost:8000") as client:
        scope = client.project("1").workspace("A").agent("X").customer("999")

        # Ingest a conversation
        await scope.add_messages([
            Message(role_type="user", content="I need a refund."),
        ])

        # Search with cascading context
        facts = await scope.search("customer refund policy")
"""

from virstack_memory.client import GraphitiClient
from virstack_memory.exceptions import (
    GraphitiAPIError,
    GraphitiConnectionError,
    GraphitiError,
    GraphitiValidationError,
)
from virstack_memory.models import (
    FactResult,
    GetMemoryResponse,
    Message,
    Result,
    SearchResults,
)
from virstack_memory.scopes import MemoryScope

__all__ = [
    "FactResult",
    "GetMemoryResponse",
    "GraphitiAPIError",
    "GraphitiClient",
    "GraphitiConnectionError",
    "GraphitiError",
    "GraphitiValidationError",
    "MemoryScope",
    "Message",
    "Result",
    "SearchResults",
]
