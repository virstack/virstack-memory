<div align="center">
  <h1>🧠 virstack-memory</h1>
  <p><b>A professional Python SDK for the Memory server with strict multi-tenant isolation.</b></p>

  <p>
    <a href="https://github.com/virstack/virstack-memory/actions"><img src="https://img.shields.io/github/actions/workflow/status/virstack/virstack-memory/test.yml?branch=main&label=tests&style=flat-square" alt="Tests"></a>
    <a href="https://pypi.org/project/virstack-memory/"><img src="https://img.shields.io/pypi/v/virstack-memory.svg?style=flat-square&color=blue" alt="PyPI Version"></a>
    <a href="https://pypi.org/project/virstack-memory/"><img src="https://img.shields.io/pypi/pyversions/virstack-memory.svg?style=flat-square" alt="Python Versions"></a>
    <a href="https://github.com/virstack/virstack-memory/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg?style=flat-square" alt="License"></a>
  </p>
</div>

---

**virstack-memory** is a fluent, async-first Python client designed specifically for integrating AI agents with the [Memory](https://github.com/getzep/graphiti) knowledge graph server. It ensures robust data isolation across complex enterprise hierarchies (Projects → Workspaces → Agents → Customers).

## ✨ Features

* ⛓️ **Fluent Scope Chaining:** Intuitive builder pattern `client.project("A").workspace("B").agent("C")`
* 🏢 **Multi-Tenant Isolation:** Automatically generates isolated database buckets (e.g., `proj_1_ws_A_agt_X_cust_999`).
* 🔎 **Cascading Search:** Retrieve combined context across all ancestor scopes in a single query.
* 🛡️ **Type Safety:** Built with Pydantic v2 DTOs that strictly match the Memory FastAPI schema.
* ⚡ **Async-First:** Powered by `httpx.AsyncClient` for high-concurrency LLM workflows.
* 🚦 **Structured Errors:** Clean exception hierarchy for connection issues, API errors, and validations.

---

## 📦 Installation

Install via pip:
```bash
pip install virstack-memory
```

Or using [uv](https://github.com/astral-sh/uv):
```bash
uv add virstack-memory
```

---

## 🚀 Quick Start

Initialize the client, build your scope, and start interacting with the graph.

```python
import asyncio
from virstack_memory import MemoryClient, Message

async def main():
    # 1. Initialize the async client
    async with MemoryClient("http://localhost:8000") as client:
        
        # 2. Build the exact isolation scope for this interaction
        memory = (
            client
            .project("virstack_prod")
            .workspace("acme_corp")
            .agent("support_bot")
            .customer("cust_123")
        )

        # 3. Fetch cascaded context (Searches Project + Workspace + Agent + Customer)
        facts = await memory.search(
            query="What are the customer's previous issues?",
            include_parents=True, 
        )
        for fact in facts:
            print(f"💡 {fact.fact}")

        # 4. Save the conversation transcript
        await memory.add_messages([
            Message(role_type="user", content="I need a refund."),
            Message(role_type="assistant", content="I'll process that right away."),
        ])

        # 5. GDPR Compliance: Delete just this specific customer's data
        await memory.delete()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🏗️ How Scope Isolation Works

The SDK constructs hierarchical `group_id` strings that map to isolated buckets within the Neo4j backend graph.

```python
scope = client.project("1").workspace("A").agent("X").customer("999")
```

| Property | Generated Value |
| :--- | :--- |
| `active_group_id` | `proj_1_ws_A_agt_X_cust_999` |
| `cascading_group_ids` | `["proj_1", "proj_1_ws_A", "proj_1_ws_A_agt_X", "proj_1_ws_A_agt_X_cust_999"]` |

> [!TIP]
> **Cascading Search Magic:**
> When executing `search(..., include_parents=True)`, the SDK sends **all** `cascading_group_ids` to the server. This allows your agent to simultaneously retrieve global policies (Project level), tenant-specific rules (Workspace level), agent personas (Agent level), and conversation history (Customer level)—all isolated but accessible when needed.

---

## 📚 API Reference

### `MemoryClient`
The root HTTP client and entry point for building scopes.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `healthcheck()` | `GET /healthcheck` | Checks if the Memory server is reachable. |
| `clear()` | `POST /clear` | ⚠️ **DANGER:** Wipes ALL graph data globally. |
| `project(id)` | — | Starts a new scope chain. |

### `MemoryScope`
The scoped execution context.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `workspace(id)` | — | Narrows scope to a Workspace. |
| `agent(id)` | — | Narrows scope to an Agent. |
| `customer(id)` | — | Narrows scope to a Customer. |
| `add_messages(...)` | `POST /messages` | Queues a conversation transcript for ingestion. |
| `add_entity_node(...)`| `POST /entity-node` | Manually creates a graph entity node. |
| `search(...)` | `POST /search` | Retrieves facts matching a natural language query. |
| `get_memory(...)` | `POST /get-memory` | Generates context directly from recent messages. |
| `get_episodes(...)` | `GET /episodes/{id}` | Fetches recent conversation episodes. |
| `delete()` | `DELETE /group/{id}` | Permanently deletes all data within this exact scope. |

---

## 🛠️ Development Setup

We use `uv` for dependency management and `make` for developer workflows.

```bash
# Install all dependencies (including dev)
make install

# Run the complete verification suite (format, lint, typecheck, tests)
make check

# Run tests
make test-unit
make test-integration
```
