# Architecture

## System Overview

`virstack-memory` is a Python SDK that acts as a typed, async client layer between application code (e.g., LiveKit voice agents) and the Virstack Memory server — a FastAPI gateway backed by a Neo4j knowledge graph.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Application Code                             │
│         (LiveKit Agent, FastAPI Service, CLI Script, etc.)          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               │  from virstack_memory import MemoryClient
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                      virstack-memory SDK                            │
│                                                                     │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────────┐ │
│  │ MemoryClient │──►│ MemoryScope  │──►│ Pydantic Models (DTOs)   │ │
│  │  (client.py) │   │  (scopes.py) │   │      (models.py)         │ │
│  └──────┬───────┘   └──────────────┘   └──────────────────────────┘ │
│         │                                                           │
│  ┌──────▼───────────────────────────────────────────────────────┐   │
│  │              Exception Hierarchy (exceptions.py)             │   │
│  │  MemoryError → MemoryConnectionError                         │   │
│  │              → MemoryAPIError                                │   │
│  │              → MemoryValidationError                         │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               │  httpx.AsyncClient (POST/GET/DELETE)
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                     Memory Server (FastAPI)                         │
│                     http://localhost:8000                           │
│                                                                     │
│  Endpoints:                                                         │
│    POST /messages        — Ingest conversation (202 Accepted)       │
│    POST /entity-node     — Create entity node (201 Created)         │
│    POST /search          — Search facts by group_ids (200)          │
│    POST /get-memory      — Contextual retrieval from messages (200) │
│    GET  /episodes/{id}   — Fetch recent episodes (200)              │
│    DELETE /group/{id}    — Delete scope data (200)                  │
│    GET  /healthcheck     — Server health probe (200)                │
│    POST /clear           — Wipe all data (200) ⚠️                   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               │  Bolt Protocol
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                        Neo4j Graph Database                         │
│                                                                     │
│  Nodes: EntityNode, EpisodicNode                                    │
│  Edges: FactEdge (with valid_at / invalid_at temporal bounds)       │
│  Isolation: group_id property on all nodes and edges                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Multi-Tenant Scope Isolation

The core architectural concept is **hierarchical scope isolation** — every piece of data in the graph is tagged with a `group_id` that encodes its exact tenancy path.

### Scope Hierarchy

```
Project
  └── Workspace
        └── Agent
              └── Customer
```

### group_id Construction

The `MemoryScope` builder walks the parent chain and concatenates prefixed IDs:

```python
client.project("acme").workspace("support").agent("bot_v2").customer("cust_42")
```

| Scope Level | `active_group_id`                           |
|:------------|:--------------------------------------------|
| Project     | `proj_acme`                                 |
| Workspace   | `proj_acme_ws_support`                      |
| Agent       | `proj_acme_ws_support_agt_bot_v2`           |
| Customer    | `proj_acme_ws_support_agt_bot_v2_cust_cust_42` |

### Prefix Map

Defined in `scopes.py`:

```python
_PREFIX_MAP = {
    "project":   "proj",
    "workspace": "ws",
    "agent":     "agt",
    "customer":  "cust",
}
```

### Cascading Search

When `search(include_parents=True)` is called at the Customer level, the SDK sends **all ancestor paths** to `/search`:

```json
{
  "group_ids": [
    "proj_acme",
    "proj_acme_ws_support",
    "proj_acme_ws_support_agt_bot_v2",
    "proj_acme_ws_support_agt_bot_v2_cust_cust_42"
  ]
}
```

This allows the search to return:
- **Project-level** facts (e.g., global company policies)
- **Workspace-level** facts (e.g., department-specific procedures)
- **Agent-level** facts (e.g., agent persona and behavior rules)
- **Customer-level** facts (e.g., individual conversation history and preferences)

---

## Module Responsibilities

### `client.py` — `MemoryClient`
- Owns the `httpx.AsyncClient` lifecycle (creation, connection pooling, close).
- Implements async context manager (`async with MemoryClient(...) as client:`).
- Provides global (non-scoped) endpoints: `healthcheck()`, `clear()`.
- Entry point for the scope chain: `project(id) → MemoryScope`.
- Internal HTTP helpers (`_post`, `_get`, `_delete`) that all scoped operations delegate to.
- Centralized error translation via `_raise_for_status()`.

### `scopes.py` — `MemoryScope`
- Implements the fluent builder: `.workspace()`, `.agent()`, `.customer()` return new `MemoryScope` instances with a `parent` backlink.
- `active_group_id` property: walks the parent chain, applies prefix map, joins with underscores.
- `cascading_group_ids` property: builds all ancestor paths for fan-out search.
- All scoped CRUD operations: `add_messages()`, `add_entity_node()`, `search()`, `get_memory()`, `get_episodes()`, `delete()`.
- Uses `__slots__` for memory efficiency.

### `models.py` — Pydantic DTOs
- **Request models:** `Message`, `AddMessagesRequest`, `AddEntityNodeRequest`, `SearchQuery`, `GetMemoryRequest`.
- **Response models:** `FactResult`, `SearchResults`, `GetMemoryResponse`, `Result`.
- All response models use `extra="ignore"` for forward compatibility.
- `Message.timestamp` defaults to `datetime.now(UTC).isoformat()`.

### `exceptions.py` — Error Hierarchy
```
MemoryError (base)
├── MemoryConnectionError   ← httpx.ConnectError, httpx.TimeoutException
├── MemoryAPIError          ← any non-2xx HTTP status (carries status_code + detail)
└── MemoryValidationError   ← HTTP 422 specifically (Pydantic validation failures)
```

---

## Data Flow

### Ingestion (Write Path)

```
Application Code
  │
  │  scope.add_messages([Message(...), ...])
  ▼
MemoryScope.add_messages()
  │  Builds payload: { group_id: active_group_id, messages: [...] }
  ▼
MemoryClient._post("/messages", payload)
  │  httpx.AsyncClient.post() → HTTP 202 Accepted
  ▼
Memory Server
  │  Queues messages for async graph processing
  ▼
Neo4j
  │  Creates EpisodicNodes + extracts FactEdges
```

### Retrieval (Read Path)

```
Application Code
  │
  │  scope.search("query", include_parents=True)
  ▼
MemoryScope.search()
  │  Builds payload: { query: "...", group_ids: cascading_group_ids, max_facts: 10 }
  ▼
MemoryClient._post("/search", payload)
  │  httpx.AsyncClient.post() → HTTP 200
  ▼
Memory Server
  │  Embeds query → vector search across specified group_ids
  ▼
Returns list[FactResult]
```

### Deletion (Delete Path)

```
Application Code
  │
  │  scope.delete()
  ▼
MemoryScope.delete()
  │  Calls DELETE /group/{active_group_id}
  ▼
MemoryClient._delete(f"/group/{group_id}")
  │  httpx.AsyncClient.delete() → HTTP 200
  ▼
Memory Server
  │  Removes all nodes/edges matching exact group_id
  ▼
Returns Result(success=True)
```

---

## CI/CD Pipeline

```
Push / PR to main
  │
  ▼
.github/workflows/test.yml
  ├── ruff format --check
  ├── ruff check
  ├── pyright
  └── pytest (unit tests only)

GitHub Release (tag)
  │
  ▼
.github/workflows/publish.yml
  ├── uv build
  └── pypa/gh-action-pypi-publish (Trusted Publishers / OIDC)
```

---

## Design Decisions

| Decision | Rationale |
|:---------|:----------|
| **httpx over aiohttp** | First-class `async/await`, Pydantic-friendly JSON handling, connection pooling. |
| **Fluent builder over config dict** | Prevents manual `group_id` string concatenation, enforces hierarchy at the type level. |
| **`extra="ignore"` on responses** | Backend can add new fields without breaking existing SDK consumers. |
| **Hatchling over uv_build** | Supports `packages = ["src/virstack_memory"]` mapping when import name differs from distribution name. |
| **`__slots__` on MemoryScope** | Memory efficiency — scope objects are created frequently in chains. |
| **pyright basic mode** | Catches real bugs without being overly strict on third-party stubs. |
| **Cascading search default** | Most agent use-cases need multi-level context; opt-out with `include_parents=False`. |
