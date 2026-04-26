"""Unit tests for MemoryScope ID generation and hierarchy building."""

from __future__ import annotations

from virstack_memory.client import GraphitiClient
from virstack_memory.scopes import MemoryScope

# ── active_group_id tests ───────────────────────────────────────────


class TestActiveGroupId:
    """Verify that active_group_id builds the correct path string."""

    def test_project_only(self, project_scope: MemoryScope) -> None:
        assert project_scope.active_group_id == "proj_1"

    def test_project_workspace(self, workspace_scope: MemoryScope) -> None:
        assert workspace_scope.active_group_id == "proj_1_ws_A"

    def test_project_workspace_agent(self, client: GraphitiClient) -> None:
        scope = client.project("1").workspace("A").agent("X")
        assert scope.active_group_id == "proj_1_ws_A_agt_X"

    def test_full_chain(self, full_scope: MemoryScope) -> None:
        assert full_scope.active_group_id == "proj_1_ws_A_agt_X_cust_999"

    def test_special_characters_in_ids(self, client: GraphitiClient) -> None:
        """IDs with hyphens, dots, etc. should pass through unchanged."""
        scope = client.project("org-123").workspace("ws.prod").customer("cust-abc")
        assert scope.active_group_id == "proj_org-123_ws_ws.prod_cust_cust-abc"

    def test_numeric_ids(self, client: GraphitiClient) -> None:
        scope = client.project("42").workspace("7").agent("3").customer("100")
        assert scope.active_group_id == "proj_42_ws_7_agt_3_cust_100"


# ── cascading_group_ids tests ───────────────────────────────────────


class TestCascadingGroupIds:
    """Verify that cascading_group_ids produces all ancestor paths."""

    def test_project_only(self, project_scope: MemoryScope) -> None:
        assert project_scope.cascading_group_ids == ["proj_1"]

    def test_project_workspace(self, workspace_scope: MemoryScope) -> None:
        assert workspace_scope.cascading_group_ids == [
            "proj_1",
            "proj_1_ws_A",
        ]

    def test_full_chain(self, full_scope: MemoryScope) -> None:
        assert full_scope.cascading_group_ids == [
            "proj_1",
            "proj_1_ws_A",
            "proj_1_ws_A_agt_X",
            "proj_1_ws_A_agt_X_cust_999",
        ]

    def test_ordering_is_root_first(self, full_scope: MemoryScope) -> None:
        ids = full_scope.cascading_group_ids
        assert ids[0] == "proj_1"
        assert ids[-1] == "proj_1_ws_A_agt_X_cust_999"


# ── Hierarchy builder tests ─────────────────────────────────────────


class TestHierarchyBuilders:
    """Verify that chaining methods produce correct scope objects."""

    def test_workspace_returns_memory_scope(self, project_scope: MemoryScope) -> None:
        ws = project_scope.workspace("W")
        assert isinstance(ws, MemoryScope)
        assert ws.scope_name == "workspace"
        assert ws.scope_id == "W"
        assert ws.parent is project_scope

    def test_agent_returns_memory_scope(self, workspace_scope: MemoryScope) -> None:
        agt = workspace_scope.agent("A1")
        assert isinstance(agt, MemoryScope)
        assert agt.scope_name == "agent"
        assert agt.scope_id == "A1"

    def test_customer_returns_memory_scope(self, client: GraphitiClient) -> None:
        cust = client.project("P").workspace("W").agent("A").customer("C")
        assert isinstance(cust, MemoryScope)
        assert cust.scope_name == "customer"
        assert cust.scope_id == "C"

    def test_repr(self, full_scope: MemoryScope) -> None:
        assert "proj_1_ws_A_agt_X_cust_999" in repr(full_scope)

    def test_skip_agent_level(self, client: GraphitiClient) -> None:
        """Workspace → Customer (skipping Agent) should still work."""
        scope = client.project("1").workspace("A").customer("999")
        assert scope.active_group_id == "proj_1_ws_A_cust_999"
        assert scope.cascading_group_ids == [
            "proj_1",
            "proj_1_ws_A",
            "proj_1_ws_A_cust_999",
        ]
