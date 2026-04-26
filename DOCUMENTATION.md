# Virstack Memory SDK: Comprehensive User Guide

Welcome to the definitive guide for `virstack-memory`, the official async Python SDK for the Virstack Memory Server. This library is designed to help AI agents persist, isolate, and recall hierarchical knowledge using a Neo4j-backed graph database.

---

## Table of Contents

1. [Core Concepts](#1-core-concepts)
2. [Installation & Setup](#2-installation--setup)
3. [Initialization & Health Checks](#3-initialization--health-checks)
4. [Scope Building & Multi-Tenant Isolation](#4-scope-building--multi-tenant-isolation)
5. [Ingesting Memory (Writing)](#5-ingesting-memory-writing)
6. [Retrieving Memory (Reading)](#6-retrieving-memory-reading)
7. [Data Deletion & Cleanup](#7-data-deletion--cleanup)
8. [Error Handling](#8-error-handling)
9. [End-to-End Example](#9-end-to-end-example)

---

## 1. Core Concepts

To effectively use `virstack-memory`, you must understand two primary classes:

*   **`MemoryClient`**: The root HTTP client. It manages the asynchronous HTTP connection pool to the Memory server and provides global endpoints (like health checks).
*   **`MemoryScope`**: A fluent builder that represents a specific "bucket" or "isolation boundary" in the database. You chain methods on the client to drill down into the exact tenant scope you need.

### The Isolation Hierarchy

The SDK enforces a strict, 4-level data hierarchy to ensure multi-tenant security:
`Project` ➔ `Workspace` ➔ `Agent` ➔ `Customer`

Every fact, entity, and message ingested into the graph is permanently bound to a specific scope level, ensuring agents only retrieve knowledge they are authorized to access.

---

## 2. Installation & Setup

### Requirements
*   Python 3.11 or higher.
*   A running instance of the Virstack Memory Server (FastAPI + Neo4j).

### Installation

**Using pip:**
```bash
pip install virstack-memory
```

**Using uv (Recommended):**
```bash
uv add virstack-memory
```

---

## 3. Initialization & Health Checks

The SDK is built entirely on Python's `asyncio`. The `MemoryClient` should be used as an asynchronous context manager to ensure HTTP connections are properly closed.

```python
import asyncio
from virstack_memory import MemoryClient

async def check_server():
    # Initialize the client with your server's URL
    async with MemoryClient("http://localhost:8000", timeout=30.0) as client:
        
        # Verify the server is reachable and Neo4j is connected
        is_healthy = await client.healthcheck()
        
        if is_healthy:
            print("✅ Server is online and ready.")
        else:
            print("❌ Server is offline or unreachable.")

asyncio.run(check_server())
```

---

## 4. Scope Building & Multi-Tenant Isolation

Before you can read or write data, you must define **where** that data belongs by building a `MemoryScope`.

You always start at the `project` level and can chain down to the `customer` level.

```python
async with MemoryClient("http://localhost:8000") as client:
    
    # 1. Project Level (Global company knowledge)
    project_scope = client.project("virstack_prod")
    
    # 2. Workspace Level (Department or specific client)
    workspace_scope = project_scope.workspace("acme_corp")
    
    # 3. Agent Level (Specific AI bot persona)
    agent_scope = workspace_scope.agent("support_bot")
    
    # 4. Customer Level (Individual end-user)
    customer_scope = agent_scope.customer("usr_999")
    
    # The resulting active group ID used in the database is:
    # "proj_virstack_prod_ws_acme_corp_agt_support_bot_cust_usr_999"
    print(customer_scope.active_group_id) 
```

> **Note:** You can stop at any level. If you are uploading a global company policy, you would use `project_scope`. If you are saving a conversation transcript, you would use `customer_scope`.

---

## 5. Ingesting Memory (Writing)

The primary way to build the knowledge graph is by feeding it conversation transcripts. The server asynchronously extracts nodes and facts from these messages in the background.

### Adding Conversation Messages

Use `add_messages` to push chat history to the server.

```python
from virstack_memory import Message

async def save_transcript(customer_scope):
    # 1. Create a list of Message objects
    messages = [
        Message(
            role_type="system", 
            content="You are a helpful support agent.",
            role="System Prompt" # Optional display name
        ),
        Message(
            role_type="user", 
            content="My shipping address changed to 123 Main St, NY.",
            role="Customer",
            # timestamp defaults to current UTC time if omitted
            timestamp="2026-04-26T10:00:00Z" 
        ),
        Message(
            role_type="assistant", 
            content="I have updated your address.",
            role="Support Bot"
        )
    ]

    # 2. Send to the server
    # Returns a Result object confirming it was queued
    result = await customer_scope.add_messages(messages)
    print(f"Success: {result.success}") 
```

### Adding Manual Entities

Sometimes you know a specific entity exists (like a Product or a strict Policy) and you want to explicitly define it in the graph without relying on LLM extraction.

```python
async def define_product(workspace_scope):
    await workspace_scope.add_entity_node(
        uuid="prod_888",
        name="Virstack Enterprise License",
        summary="Annual software license with 24/7 support SLAs."
    )
```

---

## 6. Retrieving Memory (Reading)

When an agent needs context to answer a question, you use the retrieval methods.

### Natural Language Search (Cascading Context)

The `search` method takes a natural language query and finds the most relevant facts.

By default, `search` uses **Cascading Isolation** (`include_parents=True`). If you search on a `customer_scope`, the server will retrieve facts from the Customer, the Agent, the Workspace, and the Project simultaneously.

```python
async def prepare_agent_context(customer_scope):
    # Find relevant context across the entire hierarchy
    facts = await customer_scope.search(
        query="What is the user's address and our shipping policy?",
        max_facts=15,           # How many facts to return
        include_parents=True    # Default is True: Cascade up the tree
    )

    context_string = "\n".join([f"- {f.fact}" for f in facts])
    print("Agent Context:\n", context_string)
```

If you only want facts strictly from that exact scope (e.g., only the customer's personal facts, ignoring global policies), set `include_parents=False`.

### Memory from Recent Messages

If you don't have a specific search query, but you have the last 3-4 messages of a live conversation, the server can generate an optimized search query *for you* using `get_memory`.

```python
async def get_live_context(customer_scope, recent_chat_history):
    # recent_chat_history is a list of Message objects
    facts = await customer_scope.get_memory(
        messages=recent_chat_history,
        max_facts=5
    )
    
    for fact in facts:
        print(f"Relevant Fact: {fact.fact}")
```

### Fetching Episodes

You can retrieve the raw conversation episodes (grouped message chunks) previously ingested.

```python
async def fetch_history(customer_scope):
    # Get the 5 most recent conversation episodes for this scope
    episodes = await customer_scope.get_episodes(last_n=5)
```

---

## 7. Data Deletion & Cleanup

### Scoped Deletion (GDPR / Data Retention)

You can permanently delete all nodes and edges belonging to a specific scope. Because of the multi-tenant architecture, deleting a Customer scope will **not** affect the Agent, Workspace, or Project data. 

*Note: Deleting an upper-level scope (like a Workspace) does **not** recursively delete its children. You must delete scopes individually.*

```python
async def forget_customer(client, customer_id):
    scope = client.project("virstack_prod").workspace("acme").agent("bot").customer(customer_id)
    
    # Wipes all data specific to this customer
    result = await scope.delete()
    print(f"Customer {customer_id} forgotten: {result.success}")
```

### Global Wipe (Testing Only)

To completely reset the Neo4j database across **all** tenants, use the client-level `clear()` method. **Do not use this in production.**

```python
async def reset_database(client):
    await client.clear()
```

---

## 8. Error Handling

The SDK exposes a clean, predictable exception hierarchy located in `virstack_memory.exceptions`. You should catch these instead of raw HTTP or Pydantic errors.

```python
from virstack_memory.exceptions import (
    MemoryError,           # Base class
    MemoryConnectionError, # Network issues (Timeout, Refused)
    MemoryAPIError,        # 500s, 404s, 401s
    MemoryValidationError  # 422s (Bad Payload)
)

async def safe_search(scope):
    try:
        return await scope.search("test")
        
    except MemoryConnectionError as e:
        # Fallback logic if the graph server is down
        print(f"Network error: {e}")
        return []
        
    except MemoryValidationError as e:
        # Usually means your request data was malformed
        print(f"Validation failed: {e.detail}")
        return []
        
    except MemoryAPIError as e:
        print(f"Server returned {e.status_code}: {e.detail}")
        return []
        
    except MemoryError as e:
        # Catch-all for SDK issues
        print(f"Unknown memory error: {e}")
        return []
```

---

## 9. End-to-End Example

Here is how you might integrate the SDK inside an API endpoint (e.g., a webhook called when a phone call ends).

```python
import asyncio
from typing import List
from virstack_memory import MemoryClient, Message
from virstack_memory.exceptions import MemoryError

async def handle_call_ended_webhook(
    project_id: str,
    workspace_id: str,
    agent_id: str,
    customer_phone: str,
    transcript: List[dict]
):
    """
    Webhook handler that saves a call transcript to the customer's memory.
    """
    
    # Convert raw dictionaries to SDK Message objects
    messages = [
        Message(
            role_type=msg["role"], 
            content=msg["text"],
            timestamp=msg["time"]
        )
        for msg in transcript
    ]

    try:
        # Connect to server
        async with MemoryClient("http://memory-server.internal:8000") as client:
            
            # Build the exact isolation boundary
            scope = (
                client
                .project(project_id)
                .workspace(workspace_id)
                .agent(agent_id)
                .customer(customer_phone)
            )
            
            # Queue the transcript for graph extraction
            result = await scope.add_messages(messages)
            
            if result.success:
                print(f"Successfully queued transcript for {customer_phone}")
                
    except MemoryError as e:
        # In production, log this to Datadog/Sentry
        print(f"Failed to ingest memory: {e}")

# Mock Execution
if __name__ == "__main__":
    mock_transcript = [
        {"role": "assistant", "text": "Hello, how can I help?", "time": "2026-04-26T10:00:00Z"},
        {"role": "user", "text": "Cancel my subscription.", "time": "2026-04-26T10:00:05Z"}
    ]
    
    asyncio.run(
        handle_call_ended_webhook("p1", "ws1", "bot1", "+15551234567", mock_transcript)
    )
```
