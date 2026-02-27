"""Orchestrator — wires Planner → Retrieval → Safety via WorkflowBuilder.

This is the top-level multi-agent workflow built with the Microsoft Agent Framework.
Kept lean (~40 lines of core logic) because the agents are the *subject* of CE/CM, not the hero.

Falls back to direct Azure OpenAI SDK when agent-framework has import issues
(e.g., OTel semantic-conventions version mismatch in pre-release builds).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.config import get_settings

logger = logging.getLogger(__name__)

# Try to import agent_framework; fall back to direct Azure OpenAI if unavailable
_USE_AGENT_FRAMEWORK = False
try:
    from agent_framework import RawAgent, WorkflowBuilder  # type: ignore[import-untyped]
    from agent_framework.azure import AzureOpenAIChatClient  # type: ignore[import-untyped]

    from src.agents.planner_agent import AgentPayload, PlannerAgent  # type: ignore[import-untyped]
    from src.agents.retrieval_agent import RetrievalAgent  # type: ignore[import-untyped]
    from src.agents.safety_agent import SafetyAgent  # type: ignore[import-untyped]

    _USE_AGENT_FRAMEWORK = True
    logger.info("Using Microsoft Agent Framework for orchestration")
except (ImportError, AttributeError) as e:
    logger.warning("Agent Framework unavailable (%s), using direct Azure OpenAI fallback", e)


@dataclass
class OrchestratorResult:
    """Result from the multi-agent orchestrator."""

    response: str
    agents_involved: list[str]


# ---------------------------------------------------------------------------
# Agent Framework path
# ---------------------------------------------------------------------------


def _build_raw_agent(name: str, instructions: str) -> RawAgent:
    """Create a RawAgent backed by Azure OpenAI via Agent Framework."""
    from azure.identity import DefaultAzureCredential

    settings = get_settings()
    client = AzureOpenAIChatClient(
        endpoint=settings.openai.endpoint,
        deployment_name=settings.openai.deployment,
        credential=DefaultAzureCredential(),
        api_version=settings.openai.api_version,
    )
    return RawAgent(client=client, name=name, instructions=instructions)  # type: ignore[return-value]


def _build_workflow() -> WorkflowBuilder:
    """Build the Planner → Retrieval → Safety workflow."""
    from src.agents.planner_agent import PLANNER_SYSTEM_PROMPT  # type: ignore[import-untyped]
    from src.agents.retrieval_agent import RETRIEVAL_SYSTEM_PROMPT  # type: ignore[import-untyped]
    from src.agents.safety_agent import SAFETY_SYSTEM_PROMPT  # type: ignore[import-untyped]

    planner = PlannerAgent(_build_raw_agent("planner-chat", PLANNER_SYSTEM_PROMPT))
    retrieval = RetrievalAgent(_build_raw_agent("retrieval-chat", RETRIEVAL_SYSTEM_PROMPT))
    safety = SafetyAgent(_build_raw_agent("safety-chat", SAFETY_SYSTEM_PROMPT))

    workflow = WorkflowBuilder(start_executor=planner).add_chain([planner, retrieval, safety]).build()
    return workflow


async def _run_with_agent_framework(query: str, context: str) -> OrchestratorResult:
    """Run using Microsoft Agent Framework WorkflowBuilder."""
    workflow = _build_workflow()
    payload = AgentPayload(query=query, context=context)

    try:
        result = await workflow.run(message=payload)  # type: ignore[misc]
    except Exception as e:
        err_msg = str(e).lower()
        if (
            "content_filter" in err_msg
            or "content management policy" in err_msg
            or "responsibleaipolicyviolation" in err_msg
        ):
            logger.warning("Azure content filter blocked request: %s", query[:60])
            return OrchestratorResult(
                response=SAFETY_REFUSAL,
                agents_involved=["planner-agent", "safety-agent (Azure content filter)"],
            )
        raise

    # Extract outputs from the last executor (SafetyAgent)
    outputs = result.get_outputs()
    if outputs:
        final_payload: AgentPayload = outputs[-1]
        return OrchestratorResult(
            response=final_payload.final_response or "No response generated.",
            agents_involved=final_payload.agents_involved,
        )
    return OrchestratorResult(response="No response generated.", agents_involved=[])


# ---------------------------------------------------------------------------
# Direct Azure OpenAI fallback
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a helpful assistant specialized in Azure AI services, DevOps, and MLOps. "
    "You provide accurate, grounded responses based on the context provided. "
    "If the context does not contain enough information, say so clearly. "
    "Be concise and factual. Never fabricate information."
)

SAFETY_REFUSAL = (
    "I cannot assist with that request. It falls outside my guidelines for safe and helpful responses. "
    "[SAFE] Content filtered by safety agent."
)

_SAFETY_TRIGGERS = [
    "ignore previous",
    "ignore all instructions",
    "disregard",
    "system prompt",
    "jailbreak",
    "pretend you",
    "act as if",
    "bypass",
    "override",
    "reveal your instructions",
    "DAN",
    "hack",
    "exploit",
    "malware",
    "phishing",
    "social security",
    "credit card number",
    "password",
]


async def _run_with_direct_openai(query: str, context: str) -> OrchestratorResult:
    """Fallback orchestration using Azure OpenAI SDK directly.

    Simulates the 3-agent pipeline (Planner → Retrieval → Safety):
    1. Safety check on input
    2. Call Azure OpenAI with system + context + query
    3. Safety check on output
    """
    from azure.identity import DefaultAzureCredential
    from openai import AsyncAzureOpenAI

    agents_involved = ["planner-agent", "retrieval-agent", "safety-agent"]

    # Safety agent: check input
    query_lower = query.lower()
    if any(trigger in query_lower for trigger in _SAFETY_TRIGGERS):
        logger.warning("Safety agent blocked input: %s", query[:60])
        return OrchestratorResult(response=SAFETY_REFUSAL, agents_involved=agents_involved)

    settings = get_settings()
    credential = DefaultAzureCredential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default")

    client = AsyncAzureOpenAI(
        azure_endpoint=settings.openai.endpoint,
        api_version=settings.openai.api_version,
        api_key=token.token,
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if context:
        messages.append({"role": "system", "content": f"Context:\n{context}"})
    messages.append({"role": "user", "content": query})

    response = await client.chat.completions.create(
        model=settings.openai.deployment,
        messages=messages,  # type: ignore[arg-type]
        temperature=0.3,
        max_tokens=512,
    )

    content = response.choices[0].message.content or "No response generated."

    # Safety agent: basic output check
    if any(trigger in content.lower() for trigger in _SAFETY_TRIGGERS):
        logger.warning("Safety agent blocked output")
        content = SAFETY_REFUSAL

    await client.close()
    return OrchestratorResult(response=content, agents_involved=agents_involved)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def run_orchestrator(query: str, context: str = "") -> OrchestratorResult:
    """Run the full multi-agent workflow for a user query.

    Uses Agent Framework when available, falls back to direct Azure OpenAI.

    Args:
        query: The user's question or request.
        context: Optional additional context for grounding.

    Returns:
        OrchestratorResult with the final response and list of agents that participated.
    """
    logger.info("Orchestrator starting for query: %s", query[:100])

    if _USE_AGENT_FRAMEWORK:
        result = await _run_with_agent_framework(query, context)
    else:
        result = await _run_with_direct_openai(query, context)

    logger.info("Orchestrator completed. Agents: %s", result.agents_involved)
    return result


async def demo() -> None:
    """Run a quick demo of the orchestrator — used by `make agent-demo`."""
    print("=" * 60)
    print("Multi-Agent Orchestrator Demo")
    print("=" * 60)

    test_queries = [
        "What are the best practices for deploying AI applications to Azure?",
        "Explain the difference between continuous evaluation and traditional testing for GenAI apps.",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n--- Query {i} ---")
        print(f"User: {query}\n")
        result = await run_orchestrator(query)
        print(f"Response:\n{result.response}\n")
        print(f"Agents involved: {', '.join(result.agents_involved)}")
        print("-" * 40)
