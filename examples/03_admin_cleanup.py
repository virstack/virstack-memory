"""Example: Admin cleanup — deleting specific tenant scopes.

This script demonstrates GDPR-compliant data deletion at different
isolation levels without affecting sibling or parent scopes.

Usage::

    uv run python examples/03_admin_cleanup.py
"""

import asyncio

from virstack_memory import GraphitiClient


async def main() -> None:
    async with GraphitiClient("http://localhost:8000") as client:
        # --- Delete a single customer's data ---
        # Only removes data in "proj_virstack_prod_ws_acme_corp_agt_support_bot_v2_cust_cust_12345"
        # The agent, workspace, and project data remain intact.
        customer_scope = (
            client
            .project("virstack_prod")
            .workspace("acme_corp")
            .agent("support_bot_v2")
            .customer("cust_12345")
        )
        print(f"Deleting customer scope: {customer_scope.active_group_id}")
        result = await customer_scope.delete()
        print(f"  Result: {result}")

        # --- Delete an entire agent's data ---
        # Removes everything under "proj_virstack_prod_ws_acme_corp_agt_support_bot_v2"
        # This does NOT cascade to sub-scopes automatically —
        # you'd need to delete each customer separately.
        agent_scope = (
            client
            .project("virstack_prod")
            .workspace("acme_corp")
            .agent("support_bot_v2")
        )
        print(f"\nDeleting agent scope: {agent_scope.active_group_id}")
        result = await agent_scope.delete()
        print(f"  Result: {result}")

        # --- Nuclear option: Clear ALL graph data ---
        # WARNING: This wipes the entire Neo4j database across ALL tenants!
        # Uncomment only in development/testing environments.
        # print("\n⚠️  Clearing ALL graph data...")
        # result = await client.clear()
        # print(f"  Result: {result}")

        print("\nCleanup complete.")


if __name__ == "__main__":
    asyncio.run(main())
