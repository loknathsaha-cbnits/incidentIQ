from __future__ import annotations

import json
from typing import Any
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv
from ..graph.state import IncidentState


load_dotenv()

LLM_MODEL = os.getenv("GEMINI_LLM_MODEL")
API_KEY=os.getenv("GEMINI_API_KEY")
BASE_URL=os.getenv("GEMINI_BASE_URL")

def build_fix_steps(state: IncidentState) -> list[str]:
    blast_radius = state.get("blast_radius", [])
    severity = state.get("severity", "P3")
    root_cause = state.get("root_cause", "Unknown")

    steps: list[str] = [
        "Confirm payment-service health and database connectivity.",
        "Inspect the payment-service DB connection pool and address exhausted connections.",
        "Restart or scale the payment-service DB connection pool if necessary.",
    ]

    if "api-gateway" in blast_radius:
        steps.append("Reset api-gateway circuit breakers and verify payment-service upstream calls are healthy.")
    if "frontend" in blast_radius:
        steps.append("Validate that frontend checkout traffic is no longer returning gateway or timeout errors.")
    if "order-service" in blast_radius:
        steps.append("Clear the order-service backlog and confirm payment confirmation is processing normally.")
    if "notification-service" in blast_radius:
        steps.append("Confirm notification-service queue consumers are recovered and SMTP errors are resolved.")

    if severity == "P1" and root_cause != "Unknown":
        steps.append("Escalate to on-call DB and platform engineers if recovery is not immediate.")

    steps.append("Monitor end-to-end checkout flow and service health until the incident is fully resolved.")
    return steps


def run_reporter_llm(state: IncidentState) -> dict[str, Any]:
    print("Agent thinking")
    llm = ChatOpenAI(
    model = LLM_MODEL,
    api_key = API_KEY,
    base_url = BASE_URL,
    temperature= 0.1,
    )

    root_cause = state.get("root_cause", "Unknown")
    severity = state.get("severity", "P3")
    blast_radius = state.get("blast_radius", [])
    summaries = state.get("per_service_summaries", {})

    service_summaries = "\n".join(
        f"- {service}: {summary}" for service, summary in summaries.items()
    )
    affected_services = ", ".join(blast_radius) if blast_radius else "none"

    system_message = SystemMessage(
        content=(
            "You are an incident report writer. "
            "Generate a Markdown incident report and a list of corrective action steps. "
            "Return only valid JSON with two keys: incident_report and fix_steps."
        )
    )

    human_message = HumanMessage(
        content=(
            "Incident state:\n"
            f"- root_cause: {root_cause}\n"
            f"- severity: {severity}\n"
            f"- affected_services: {affected_services}\n"
            f"- service_summaries:\n{service_summaries}\n\n"
            "Produce a JSON object like:\n"
            '{\n'
            '  "incident_report": "...",\n'
            '  "fix_steps": ["...", "..."]\n'
            '}\n'
            "The incident_report should be formatted in Markdown."
        )
    )

    response = llm.invoke([system_message, human_message])
    text = response.content.strip()

    try:
        output = json.loads(text)
    except json.JSONDecodeError:
        return {}

    if not isinstance(output, dict):
        return {}

    return output


def reporter(state: IncidentState) -> dict[str, Any]:
    print("Reporter Working")
    llm_output = run_reporter_llm(state)

    incident_report = llm_output.get("incident_report", "")
    fix_steps = llm_output.get("fix_steps")

    if not incident_report:
        root_cause = state.get("root_cause", "Unknown")
        severity = state.get("severity", "P3")
        blast_radius = state.get("blast_radius", [])
        summaries = state.get("per_service_summaries", {})

        lines: list[str] = [
            "# Incident Report",
            "",
            f"**Severity:** {severity}",
            "",
            f"**Root cause:** {root_cause}",
            "",
            "## Affected services",
        ]

        if blast_radius:
            lines.extend([f"- {service}" for service in blast_radius])
        else:
            lines.append("- No secondary services were identified as affected.")

        lines.extend(["", "## Service summaries"])
        for service, summary in summaries.items():
            lines.append(f"- **{service}**: {summary}")

        lines.extend(["", "## Recommended fix steps"])
        fallback_fix_steps = build_fix_steps(state)
        if fallback_fix_steps:
            lines.extend(
                [f"{idx}. {step}" for idx, step in enumerate(fallback_fix_steps, start=1)]
            )
        else:
            lines.append(
                "1. No specific fix steps were generated. Review service logs and investigate manually."
            )

        incident_report = "\n".join(lines).strip()
        fix_steps = fallback_fix_steps

    if not isinstance(fix_steps, list):
        fix_steps = build_fix_steps(state)

    return {
        "incident_report": incident_report,
        "fix_steps": fix_steps,
        "messages": state.get("messages", []),
    }