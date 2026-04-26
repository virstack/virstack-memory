# CLAUDE.md

## Identity
This is `virstack-memory` (PyPI: `virstack-memory`, import: `virstack_memory`), an async Python SDK for the Virstack Memory server — a Neo4j-backed knowledge graph accessed via a FastAPI gateway.

## Quick Reference

### Build & Test
```bash
make install        # uv sync --all-extras
make check          # format → lint → typecheck → test-unit (run this before every PR)
make test-unit      # unit tests only (no server needed)
make test-integration  # requires Memory server at localhost:8000
```

### Project Layout
```
src/virstack_memory/
├── __init__.py      # Public API surface — all exports live here
├── client.py        # MemoryClient — httpx.AsyncClient wrapper, global endpoints
├── scopes.py        # MemoryScope — fluent builder, group_id construction, scoped CRUD
├── models.py        # Pydantic v2 DTOs (Message, FactResult, SearchResults, Result, etc.)
└── exceptions.py    # MemoryError → MemoryConnectionError, MemoryAPIError, MemoryValidationError

tests/
├── conftest.py      # Shared fixtures (mock_http, client, full_scope, etc.)
├── test_scopes.py   # group_id generation, cascading_group_ids, hierarchy builders
├── test_client.py   # HTTP lifecycle, healthcheck, error mapping, payload verification
└── test_integration.py  # Live server tests (auto-skipped if offline)

examples/            # Runnable scripts demonstrating SDK usage
```

### Key Architectural Patterns

1. **Fluent Builder Pattern** — `MemoryClient.project()` returns `MemoryScope`, which chains `.workspace()` → `.agent()` → `.customer()`. Each level appends to the `group_id` path using `_PREFIX_MAP` in `scopes.py`.

2. **Cascading Search** — `MemoryScope.cascading_group_ids` returns all ancestor paths (root-first) so `/search` can fan out across isolation levels.

3. **Error Wrapping** — All `httpx` exceptions are caught at the `MemoryClient._post/_get/_delete` boundary and re-raised as SDK-specific exceptions. The static method `_raise_for_status` handles HTTP status → exception mapping.

4. **Forward Compatibility** — All response Pydantic models use `extra="ignore"` to tolerate new backend fields.

## Rules

### MUST
- Run `make check` before declaring any task complete.
- Use `extra="ignore"` on all new response models.
- Wrap all new HTTP calls through `MemoryClient._post`, `_get`, or `_delete` — never call `self.http` directly from `MemoryScope`.
- Route all scoped operations through `MemoryScope` and its `active_group_id` — never manually construct `group_id` strings.
- Use `snake_case` for all Python identifiers and JSON payload keys.

### MUST NOT
- Hardcode URLs, API keys, or secrets anywhere.
- Add synchronous blocking I/O (`time.sleep`, `requests`) in the async codebase.
- Expose raw `httpx` exceptions to SDK consumers.
- Remove or modify `extra="ignore"` from existing response models.
- Change public method signatures on `MemoryClient` or `MemoryScope` without explicit approval (breaking change).

### SHOULD
- Add a test for every new method (both happy path and error handling).
- Define new fixtures in `tests/conftest.py` rather than duplicating setup.
- Use `TYPE_CHECKING` guards for imports that would create circular dependencies (see `scopes.py`).
- Keep the `__all__` list in `__init__.py` sorted (enforced by ruff rule `RUF022`).

## Configuration
- **Python:** ≥ 3.11
- **Type checker:** `pyright` (basic mode)
- **Linter/Formatter:** `ruff` (line-length 100, rules: E, W, F, I, N, UP, B, RUF)
- **Test runner:** `pytest` with `pytest-asyncio` (auto mode)
- **Build backend:** `hatchling`
- **CI:** GitHub Actions — `.github/workflows/test.yml` (lint + typecheck + test)
- **CD:** GitHub Actions — `.github/workflows/publish.yml` (PyPI via Trusted Publishers/OIDC)
