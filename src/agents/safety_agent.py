"""Safety Agent — content-safety guardrail that filters unsafe outputs.

Uses the Microsoft Agent Framework Executor pattern (rc2 API).
"""

import logging

from agent_framework import Executor, Message, RawAgent, WorkflowContext, handler

from src.agents.planner_agent import AgentPayload

logger = logging.getLogger(__name__)

SAFETY_SYSTEM_PROMPT = (
    "You are a Safety Agent. Review the proposed response for any content safety issues: "
    "harmful content, PII leakage, bias, or policy violations. "
    "If the content is safe, return it unchanged with a brief '[SAFE]' prefix. "
    "If unsafe, redact the problematic parts and prefix with '[REDACTED]'. "
    "Always explain what you checked."
)


class SafetyAgent(Executor):
    """Content-safety guardrail — filters unsafe outputs before returning to user."""

    def __init__(self, agent: RawAgent) -> None:
        super().__init__(id="safety-agent")
        self._agent = agent

    @handler
    async def handle(self, message: AgentPayload, ctx: WorkflowContext[AgentPayload, AgentPayload]) -> None:
        """Review the grounded response for safety issues."""
        logger.info("SafetyAgent invoked — reviewing response")

        review_msg = Message(
            role="user",
            text=f"Review the following response for safety issues:\n\n{message.grounded_response}",
        )
        response = await self._agent.run([review_msg])  # type: ignore[misc]

        final_response: str = response.text or "No safety review generated."
        message.final_response = final_response
        message.agents_involved.append("safety-agent")
        logger.info("SafetyAgent result: %s", final_response[:120])
        await ctx.yield_output(message)
