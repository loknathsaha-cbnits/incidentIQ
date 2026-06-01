from langgraph.graph import END, StateGraph
from .state import IncidentState
from ..tools.agent import agent
from ..tools.log_reader import log_reader
from ..tools.reporter import reporter

workflow = StateGraph(IncidentState)

workflow.add_node("log_reader", log_reader)
workflow.add_node("agent", agent)
workflow.add_node("reporter", reporter)

workflow.set_entry_point("log_reader")
workflow.add_edge("log_reader", "agent")
workflow.add_edge("agent", "reporter")
workflow.add_edge("reporter", END)

graph = workflow.compile()