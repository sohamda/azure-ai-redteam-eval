"""Planner Agent — decomposes user requests and decides which agents to invoke.

Uses the Microsoft Agent Framework Executor pattern (rc2 API).
"""

import logging
from dataclasses import dataclass, field

from agent_framework import Executor, Message, RawAgent, WorkflowContext, handler

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = (
    "You are a Planner Agent. Your job is to analyze the user's request, break it into sub-tasks, "
    "and produce a concise plan. Identify whether the request needs grounding (retrieval) and/or "
    "a safety check. Output a short plan with numbered steps."
)


@dataclass
class AgentPayload:
    """Message payload passed between agents in the workflow."""

    query: str
    context: str = ""
    plan: str = ""
    grounded_response: str = ""
    final_response: str = ""
    agents_involved: list[str] = field(default_factory=list)


class PlannerAgent(Executor):
    """Plans tasks and delegates to other agents in the workflow."""

    def __init__(self, agent: RawAgent) -> None:
        super().__init__(id="planner-agent")
        self._agent = agent

    @handler
    async def handle(self, message: AgentPayload, ctx: WorkflowContext[AgentPayload]) -> None:
        """Analyze the user query and produce a plan."""
        logger.info("PlannerAgent invoked for query: %s", message.query[:80])

        user_msg = Message(role="user", text=message.query)
        response = await self._agent.run([user_msg])  # type: ignore[misc]

        plan_text: str = response.text or "No plan generated."
        message.plan = plan_text
        message.agents_involved.append("planner-agent")

        logger.info("PlannerAgent produced plan: %s", plan_text[:120])
        await ctx.send_message(message)
