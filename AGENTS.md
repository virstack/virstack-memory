# AGENTS.md

## Project Overview
This repository contains `virstack_memory`, an asynchronous Python SDK/client for the Virstack Memory FastAPI server. It provides a fluent builder pattern for multi-tenant graph memory isolation, handling API requests, error formatting, and Pydantic validation.

## Commands
*Note: Refer to the `Makefile` for exact command aliases.*
- **Install dependencies:** `make install` (runs `uv sync --all-extras`)
- **Run all tests:** `make test` or `uv run pytest tests/ -v`
- **Run unit tests only:** `make test-unit`
- **Run integration tests:** `make test-integration` (requires a running Memory server)
- **Format:** `make format` (runs `uv run ruff format src tests`)
- **Lint:** `make lint` (runs `uv run ruff check src tests --fix`)
- **Type Check:** `make typecheck` (runs `uv run pyright`)
- **Full check suite:** `make check` (format → lint → typecheck → test-unit)

## Architecture Boundaries & Patterns

### 1. Standard Module Structure
When extending the SDK, adhere to the existing file responsibilities rather than inventing new patterns.
- `client.py`: The `MemoryClient` base class. Handles the underlying `httpx.AsyncClient` lifecycle, global endpoints (`/healthcheck`, `/clear`), and provides the entry point for the scope builder (`.project()`).
- `scopes.py`: The `MemoryScope` class. Implements the fluent builder pattern (Project → Workspace → Agent → Customer) to construct `group_id` strings and cascading search arrays. Contains all scoped CRUD operations.
- `models.py`: Pydantic DTOs for all API requests and responses.
- `exceptions.py`: Custom exception hierarchy inheriting from `MemoryError`.
- `tests/`: Colocated `test_*.py` files matching the `src/virstack_memory` structure.

### 2. Pydantic Models & Forward Compatibility
- **Extensibility:** All response models in `models.py` **MUST** include `extra="ignore"`. This ensures the SDK does not crash if the backend server adds new fields to its JSON responses in the future.

## Core Coding Standards

### 1. Task Completion & Verification (CRITICAL)
- Whenever you make a modification to the codebase, you **MUST** run the type checker (`make typecheck` or `uv run pyright`) to catch any type-hint discrepancies.
- Before considering a task finished or ready for a PR, you **MUST** run the test suite (`make test-unit`) to ensure the SDK functions correctly.

### 2. Naming Conventions (CRITICAL)
- **Strictly use `snake_case`** for all Pydantic model fields, API request/response payload keys, and database properties.
- **Never** use `camelCase` at the API boundary or within Python class properties.

### 3. Environment Variables & Secrets (CRITICAL)
- **Never** hardcode credentials, API keys, or URLs anywhere in the codebase or test files.
- Configuration (like the Memory server URL) should be passed into the `MemoryClient` instantiation, often loaded from environment variables by the caller.
- If testing requires mock keys/URLs, use placeholder strings (e.g., `http://test-server`) or `.env.test` files. If adding new environment variable requirements for tests or examples:
  1. Add it to `.env.example`.
  2. Update the local `.env` file.

### 4. Tenant Isolation (CRITICAL)
- The SDK's primary purpose is securing tenant data boundaries.
- **Rule:** Never bypass the `MemoryScope` builder when making scoped CRUD API calls (like `/messages` or `/search`). The `group_id` must always be constructed via `active_group_id` or `cascading_group_ids` to guarantee cross-tenant isolation.

### 5. Error Handling
- **Never** expose raw `httpx` exceptions (`httpx.ConnectError`, `httpx.TimeoutException`, `httpx.HTTPStatusError`) to the end user.
- **Always** catch network or HTTP errors and wrap them in the custom exceptions defined in `exceptions.py` (e.g., `MemoryConnectionError`, `MemoryAPIError`, `MemoryValidationError`).
- Let `MemoryClient._raise_for_status` handle non-2xx response translation.

## Testing Standards
- **Framework:** `pytest` with `pytest-asyncio` for asynchronous tests.
- **Async mode:** `asyncio_mode = "auto"` is configured in `pyproject.toml` — no need for `@pytest.mark.asyncio` decorators.
- **Fixtures:** Define shared fixtures (like mock clients or dummy `group_id` strings) in `tests/conftest.py`.
- **Mocking:** Do not make real HTTP requests in unit tests. Mock the `httpx.AsyncClient` responses using `unittest.mock.AsyncMock`.
- **Coverage Requirements:** Any new method added to `MemoryScope` or `MemoryClient` must have an accompanying test in `tests/` verifying standard execution and exception handling.

## Security & Boundaries
- **Ask first before:**
  - Adding new third-party dependencies to `pyproject.toml`.
  - Changing the signature of public methods in `MemoryClient` or `MemoryScope` (this breaks downstream users).
- **Never:**
  - Commit `.env` files.
  - Introduce synchronous blocking I/O calls (`time.sleep`, `requests.get`) inside the async SDK architecture.
