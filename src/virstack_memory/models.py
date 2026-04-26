"""Pydantic DTOs matching the Graphiti FastAPI server schema exactly.

These models are derived from the server's ``graph_service.dto`` module
(https://github.com/getzep/graphiti) and are configured with
``extra="ignore"`` to tolerate future field additions from the backend
without crashing the client.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

# ── Request Models ──────────────────────────────────────────────────


class Message(BaseModel, extra="ignore"):
    """A single conversation message to ingest via ``POST /messages``.

    Attributes:
        content: The text content of the message.
        role_type: One of ``user``, ``assistant``, or ``system``.
        role: Optional custom role label (e.g. speaker name).
        uuid: Optional client-generated UUID for the episodic node.
        name: Optional name for the episodic node.
        timestamp: ISO-8601 datetime string; defaults to now (UTC).
        source_description: Freeform description of the message source.
    """

    content: str = Field(..., description="The content of the message")
    role_type: Literal["user", "assistant", "system"] = Field(
        ..., description="The role type of the message"
    )
    role: str | None = Field(
        default=None,
        description="Custom role label used alongside role_type (speaker name, bot name, etc.)",
    )
    uuid: str | None = Field(
        default=None, description="Client-generated UUID for the episodic node"
    )
    name: str = Field(default="", description="Name for the episodic node")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO-8601 timestamp of the message",
    )
    source_description: str = Field(default="", description="Description of the message source")


class AddMessagesRequest(BaseModel):
    """Payload for ``POST /messages``."""

    group_id: str = Field(..., description="The group id of the messages to add")
    messages: list[Message] = Field(..., description="The messages to add")


class AddEntityNodeRequest(BaseModel):
    """Payload for ``POST /entity-node``."""

    uuid: str = Field(..., description="The uuid of the node to add")
    group_id: str = Field(..., description="The group id of the node to add")
    name: str = Field(..., description="The name of the node to add")
    summary: str = Field(default="", description="The summary of the node to add")


class SearchQuery(BaseModel):
    """Payload for ``POST /search``."""

    query: str = Field(..., description="The search query text")
    group_ids: list[str] | None = Field(
        default=None, description="Group IDs to scope the search to"
    )
    max_facts: int = Field(default=10, description="Maximum number of facts to retrieve")


class GetMemoryRequest(BaseModel):
    """Payload for ``POST /get-memory``."""

    group_id: str = Field(..., description="The group id of the memory to get")
    max_facts: int = Field(default=10, description="Maximum number of facts to retrieve")
    center_node_uuid: str | None = Field(
        default=None, description="UUID of the node to center retrieval on"
    )
    messages: list[Message] = Field(..., description="Messages to build the retrieval query from")


# ── Response Models ─────────────────────────────────────────────────


class FactResult(BaseModel, extra="ignore"):
    """A single fact/edge returned by the search or get-memory endpoints."""

    uuid: str
    name: str
    fact: str
    valid_at: datetime | None = None
    invalid_at: datetime | None = None
    created_at: datetime
    expired_at: datetime | None = None


class SearchResults(BaseModel, extra="ignore"):
    """Response body from ``POST /search``."""

    facts: list[FactResult]


class GetMemoryResponse(BaseModel, extra="ignore"):
    """Response body from ``POST /get-memory``."""

    facts: list[FactResult]


class Result(BaseModel, extra="ignore"):
    """Generic success/failure response from mutation endpoints."""

    message: str
    success: bool
