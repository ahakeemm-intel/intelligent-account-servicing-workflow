"""
LangGraph Pipeline

Graph: START → validation_agent → document_processor → confidence_scorer → summary_generator → END

After the graph completes, the caller persists results to the DB and sets
change_request.status = AI_VERIFIED_PENDING_HUMAN.

The graph never writes to RPS — that path only exists in the checker approval endpoint.
"""
from langgraph.graph import StateGraph, START, END
from app.agents.state import RequestState
from app.agents.nodes.validation import validation_agent
from app.agents.nodes.document_processor import document_processor
from app.agents.nodes.confidence_scorer import confidence_scorer
from app.agents.nodes.summary_generator import summary_generator
from loguru import logger


def _should_continue_after_validation(state: RequestState) -> str:
    """Stop early if customer/field validation fails."""
    if state.get("validation_errors"):
        logger.warning("graph | validation failed — routing to summary directly")
        return "summary_generator"  # Generate an error summary rather than crashing
    return "document_processor"


def build_graph() -> StateGraph:
    graph = StateGraph(RequestState)

    graph.add_node("validation_agent", validation_agent)
    graph.add_node("document_processor", document_processor)
    graph.add_node("confidence_scorer", confidence_scorer)
    graph.add_node("summary_generator", summary_generator)

    graph.add_edge(START, "validation_agent")
    graph.add_conditional_edges(
        "validation_agent",
        _should_continue_after_validation,
        {
            "document_processor": "document_processor",
            "summary_generator": "summary_generator",
        },
    )
    graph.add_edge("document_processor", "confidence_scorer")
    graph.add_edge("confidence_scorer", "summary_generator")
    graph.add_edge("summary_generator", END)

    return graph.compile()


# Module-level compiled graph (compiled once, reused per request)
pipeline = build_graph()


async def run_pipeline(initial_state: RequestState) -> RequestState:
    """
    Run the full agent pipeline asynchronously.
    Returns the final state after all nodes have executed.
    Times out after 5 minutes to prevent the background task hanging forever.
    """
    import asyncio
    logger.info("pipeline | START | request={}", initial_state["request_id"])
    try:
        result = await asyncio.wait_for(pipeline.ainvoke(initial_state), timeout=300)
    except asyncio.TimeoutError:
        logger.error("pipeline | TIMEOUT | request={}", initial_state["request_id"])
        result = {
            **initial_state,
            "pipeline_errors": ["Pipeline timed out after 5 minutes"],
            "ai_summary": "Pipeline processing timed out. Manual review required.",
            "ai_recommendation": "FLAG_FOR_REVIEW",
            "overall_confidence": 0.0,
            "field_scores": {},
            "forgery_result": "FLAG",
        }
    logger.info(
        "pipeline | END | request={} | confidence={} | recommendation={}",
        result.get("request_id"),
        result.get("overall_confidence"),
        result.get("ai_recommendation"),
    )
    return result
