"""Virstack Memory SDK — Python client for the Memory server.

Quick start::

    from virstack_memory import MemoryClient, Message

    async with MemoryClient("http://localhost:8000") as client:
        scope = client.project("1").workspace("A").agent("X").customer("999")

        # Ingest a conversation
        await scope.add_messages([
            Message(role_type="user", content="I need a refund."),
        ])

        # Search with cascading context
        facts = await scope.search("customer refund policy")
"""

from virstack_memory.client import MemoryClient
from virstack_memory.exceptions import (
    MemoryAPIError,
    MemoryConnectionError,
    MemoryError,
    MemoryValidationError,
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
    "MemoryAPIError",
    "MemoryClient",
    "MemoryConnectionError",
    "MemoryError",
    "MemoryValidationError",
    "MemoryScope",
    "Message",
    "Result",
    "SearchResults",
]
