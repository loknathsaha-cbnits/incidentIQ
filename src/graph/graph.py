from langgraph.graph import END, StateGraph

from src.tools.emailer import emailer

from ..tools.display import display
from ..tools.github_node import github_node
from .state import IncidentState
from ..tools.agent import agent
from ..tools.log_reader import log_reader
from ..tools.reporter import reporter

def decision(state: IncidentState) -> IncidentState:
    severity = state["severity"]  
    if severity in ("P1", "P2"):
        state["next_action"] = "create_issue"
    else:
        state["next_action"] = "end"
    return state

def decide_action(state: IncidentState) -> str:
    return state["next_action"]

workflow = StateGraph(IncidentState)

workflow.add_node("log_reader", log_reader)
workflow.add_node("agent", agent)
workflow.add_node("reporter", reporter)
workflow.add_node("decision", decision)
workflow.add_node("github_node", github_node)
workflow.add_node("emailer", emailer) 
workflow.add_node("display", display)

workflow.set_entry_point("log_reader")
workflow.add_edge("log_reader", "agent")
workflow.add_edge("agent", "reporter")
workflow.add_edge("reporter", "decision")
workflow.add_conditional_edges(
    "decision",
    decide_action,                                
    {
        "create_issue": "github_node",            
        "end": END                                
    }
)

workflow.add_edge("github_node", "display")
workflow.add_edge("display",     "emailer")
workflow.add_edge("emailer", END)

graph = workflow.compile()