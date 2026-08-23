"""Build and manage the code review graph."""

import logging
from langgraph.graph import StateGraph

from app.graph.state import ReviewState
from app.graph.nodes.preprocess import preprocess_diff
from app.graph.nodes.reviewer import review_code
from app.graph.nodes.summarize import summarize_findings

logger = logging.getLogger("code_review_agent.graph")


def build_review_graph():
    """Build the LangGraph code review pipeline.
    
    The graph follows this flow:
    START → preprocess_diff → review_code → summarize_findings → END
    
    Returns:
        A compiled StateGraph instance ready to invoke
    """
    graph = StateGraph(ReviewState)
    
    # Add nodes
    graph.add_node("preprocess", preprocess_diff)
    graph.add_node("reviewer", review_code)
    graph.add_node("summarize", summarize_findings)
    
    # Add edges
    graph.add_edge("preprocess", "reviewer")
    graph.add_edge("reviewer", "summarize")
    
    # Set entry point
    graph.set_entry_point("preprocess")
    
    # Set finish point
    graph.set_finish_point("summarize")
    
    logger.info("Review graph built: preprocess -> reviewer -> summarize")
    
    return graph.compile()


# Global graph instance
_graph = None


def get_review_graph():
    """Get or create the compiled review graph.
    
    Returns:
        Compiled StateGraph instance
    """
    global _graph
    if _graph is None:
        _graph = build_review_graph()
    return _graph
