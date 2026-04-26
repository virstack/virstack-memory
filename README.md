# virstack-memory

A Python SDK for interacting with the [Graphiti](https://github.com/getzep/graphiti) memory server, providing fluent multi-tenant scope isolation for AI agent knowledge graphs.

## Features

- **Fluent scope chaining** — `client.project("1").workspace("A").agent("X").customer("999")`
- **Cascading search** — automatically queries across all ancestor scopes for rich context
- **Multi-tenant isolation** — each scope level generates a unique `group_id` path (e.g. `proj_1_ws_A_agt_X_cust_999`)
- **Typed models** — Pydantic v2 DTOs matching the Graphiti FastAPI server schema
- **Async-first** — built on `httpx.AsyncClient` for high-throughput environments
- **Error handling** — structured exceptions for connection, validation, and API errors

## Installation

```bash
pip install virstack-memory
```

Or with uv:

```bash
uv add virstack-memory
```

## Quick Start

```python
import asyncio
from virstack_memory import GraphitiClient, Message

async def main():
    async with GraphitiClient("http://localhost:8000") as client:
        # Build the scope chain for a specific customer call
        memory = (
            client
            .project("virstack_prod")
            .workspace("acme_corp")
            .agent("support_bot")
            .customer("cust_123")
        )

        # 1. Fetch multi-layered context before the call
        facts = await memory.search(
            query="What are the customer's previous issues?",
            include_parents=True,  # searches across all ancestor scopes
        )
        for fact in facts:
            print(f"  {fact.fact}")

        # 2. Save the transcript after the call
        await memory.add_messages([
            Message(role_type="user", content="I need a refund."),
            Message(role_type="assistant", content="I'll process that right away."),
        ])

        # 3. Delete just the customer's data (GDPR compliance)
        await memory.delete()

asyncio.run(main())
```

## How Scope Isolation Works

The SDK builds hierarchical `group_id` strings that map to isolated buckets in the Neo4j graph:

```
client.project("1").workspace("A").agent("X").customer("999")
```

| Property              | Value                                                                        |
| --------------------- | ---------------------------------------------------------------------------- |
| `active_group_id`     | `proj_1_ws_A_agt_X_cust_999`                                                |
| `cascading_group_ids` | `["proj_1", "proj_1_ws_A", "proj_1_ws_A_agt_X", "proj_1_ws_A_agt_X_cust_999"]` |

When searching with `include_parents=True`, all cascading IDs are sent to the `/search` endpoint, allowing the AI agent to access:
- **Project-level** knowledge (global policies)
- **Workspace-level** knowledge (tenant-specific rules)
- **Agent-level** knowledge (agent persona/behavior)
- **Customer-level** knowledge (individual conversation history)

## API Reference

### `GraphitiClient`

| Method                   | Endpoint           | Description                           |
| ------------------------ | ------------------ | ------------------------------------- |
| `healthcheck()`          | `GET /healthcheck` | Check server health                   |
| `clear()`                | `POST /clear`      | ⚠️ Wipe ALL graph data                |
| `project(id)`            | —                  | Start scope chain                     |

### `MemoryScope`

| Method                              | Endpoint                    | Description                       |
| ----------------------------------- | --------------------------- | --------------------------------- |
| `workspace(id)` / `agent(id)` / `customer(id)` | —              | Chain scope deeper                |
| `add_messages(messages)`            | `POST /messages`            | Ingest conversation (202)         |
| `add_entity_node(uuid, name)`       | `POST /entity-node`         | Create manual entity (201)        |
| `search(query, ...)`                | `POST /search`              | Search facts (200)                |
| `get_memory(messages, ...)`         | `POST /get-memory`          | Context from messages (200)       |
| `get_episodes(last_n=10)`           | `GET /episodes/{group_id}`  | Fetch recent episodes (200)       |
| `delete()`                          | `DELETE /group/{group_id}`  | Delete scope data (200)           |

## Development

```bash
# Install all dependencies
make install

# Run all checks (format + lint + typecheck + tests)
make check

# Run only unit tests
make test-unit

# Run integration tests (requires running Graphiti server)
make test-integration
```

## License

MIT
