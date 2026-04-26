"""Example: Saving a LiveKit transcript after a call ends.

This script demonstrates how to ingest a conversation transcript
into the customer's memory scope after a SIP/WebRTC call completes.

Usage::

    uv run python examples/01_call_ingestion.py
"""

import asyncio

from virstack_memory import MemoryClient, Message


async def main() -> None:
    async with MemoryClient("http://localhost:8000") as client:
        # Verify server is up
        healthy = await client.healthcheck()
        print(f"Server healthy: {healthy}")
        if not healthy:
            print("Memory server is not running. Start it first.")
            return

        # Build the scope chain for this specific call
        call_memory = (
            client
            .project("virstack_prod")
            .workspace("acme_corp")
            .agent("support_bot_v2")
            .customer("cust_12345")
        )

        print(f"Scope: {call_memory}")
        print(f"Active group_id: {call_memory.active_group_id}")
        print(f"Cascading IDs:   {call_memory.cascading_group_ids}")

        # Ingest the conversation transcript
        result = await call_memory.add_messages([
            Message(
                role_type="user",
                role="Customer",
                content="Hi, I placed an order last week but haven't received it yet.",
                timestamp="2026-04-26T10:00:00Z",
            ),
            Message(
                role_type="assistant",
                role="Support Agent",
                content="I can see your order #ORD-789. It's currently in transit and should arrive by Thursday.",
                timestamp="2026-04-26T10:00:15Z",
            ),
            Message(
                role_type="user",
                role="Customer",
                content="Great, thanks! Also, can you update my email to john.new@example.com?",
                timestamp="2026-04-26T10:00:30Z",
            ),
            Message(
                role_type="assistant",
                role="Support Agent",
                content="Done! Your email has been updated to john.new@example.com.",
                timestamp="2026-04-26T10:00:45Z",
            ),
        ])

        print(f"\nIngestion result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
