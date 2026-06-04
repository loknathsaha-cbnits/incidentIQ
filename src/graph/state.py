from typing import TypedDict, Annotated
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage

class IncidentState(TypedDict):
    scenario: str                        # "cascade" | "healthy" | "partial"
    logs_dir: str                        # path to data/logs/

    raw_logs: dict[str, str]             # {"payment-service": "...raw log text..."}

    per_service_summaries: dict[str, str]  # {"payment-service": "DB pool exhausted..."}
    root_cause: str                        # "payment-service DB connection pool exhaustion"
    blast_radius: list[str]                # ["api-gateway", "order-service", "notification-service"]
    severity: str                          # "P1" | "P2" | "P3"

    incident_report: str                   # full structured markdown report
    fix_steps: list[str]                   # ordered list of what to do right now

    messages: Annotated[list[BaseMessage], add_messages]

    next_action: str          
    github_issue_url: str