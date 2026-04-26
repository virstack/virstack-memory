"""Example: Fetching cascaded search context before a call.

This script demonstrates how to query multi-layered memory
(project policies → workspace rules → agent persona → customer history)
before an AI agent begins a conversation.

Usage::

    uv run python examples/02_precall_context.py
"""

import asyncio

from virstack_memory import MemoryClient


async def main() -> None:
    async with MemoryClient("http://localhost:8000") as client:
        # Build scope for the incoming call
        call_memory = (
            client
            .project("virstack_prod")
            .workspace("acme_corp")
            .agent("support_bot_v2")
            .customer("cust_12345")
        )

        # --- Cascading search (default) ---
        # This queries across ALL levels:
        #   proj_virstack_prod
        #   proj_virstack_prod_ws_acme_corp
        #   proj_virstack_prod_ws_acme_corp_agt_support_bot_v2
        #   proj_virstack_prod_ws_acme_corp_agt_support_bot_v2_cust_cust_12345
        print("=== Cascading search (all scopes) ===")
        facts = await call_memory.search(
            query="What are the customer's previous issues and our refund policy?",
            max_facts=10,
            include_parents=True,
        )
        for fact in facts:
            print(f"  [{fact.uuid[:8]}] {fact.fact}")

        # --- Scoped search (single level) ---
        # Only searches the exact customer bucket
        print("\n=== Customer-only search ===")
        customer_facts = await call_memory.search(
            query="customer preferences",
            max_facts=5,
            include_parents=False,
        )
        for fact in customer_facts:
            print(f"  [{fact.uuid[:8]}] {fact.fact}")

        # --- Workspace-level search ---
        # Search only project + workspace (no agent/customer)
        ws_memory = client.project("virstack_prod").workspace("acme_corp")
        print("\n=== Workspace policy search ===")
        policies = await ws_memory.search(
            query="refund and return policies",
            max_facts=5,
        )
        for fact in policies:
            print(f"  [{fact.uuid[:8]}] {fact.fact}")

        print(f"\nTotal facts found: {len(facts) + len(customer_facts) + len(policies)}")


if __name__ == "__main__":
    asyncio.run(main())
