"""Retrieval Agent — RAG / grounding agent that fetches context for the user query.

Uses the Microsoft Agent Framework Executor pattern (rc2 API).
"""

import logging

from agent_framework import Executor, Message, RawAgent, WorkflowContext, handler

from src.agents.planner_agent import AgentPayload

logger = logging.getLogger(__name__)

RETRIEVAL_SYSTEM_PROMPT = (
    "You are a Retrieval Agent. Given a user query and a plan, provide grounded, factual information "
    "to answer the query. Cite sources where possible. If you don't have relevant information, "
    "say so clearly. Do not fabricate facts."
)


class RetrievalAgent(Executor):
    """Fetches grounding context for the user query (RAG pattern)."""

    def __init__(self, agent: RawAgent) -> None:
        super().__init__(id="retrieval-agent")
        self._agent = agent

    @handler
    async def handle(self, message: AgentPayload, ctx: WorkflowContext[AgentPayload]) -> None:
        """Retrieve grounding information based on the plan and user query."""
        logger.info("RetrievalAgent invoked for query: %s", message.query[:80])

        prompt = f"Query: {message.query}\n\nPlan:\n{message.plan}"
        if message.context:
            prompt += f"\n\nContext:\n{message.context}"
        user_msg = Message(role="user", text=prompt)
        response = await self._agent.run([user_msg])  # type: ignore[misc]

        grounded_text: str = response.text or "No grounded response generated."
        message.grounded_response = grounded_text
        message.agents_involved.append("retrieval-agent")

        logger.info("RetrievalAgent produced grounded response: %s", grounded_text[:120])
        await ctx.send_message(message)
