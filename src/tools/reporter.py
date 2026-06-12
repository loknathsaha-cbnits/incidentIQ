from __future__ import annotations

import json
import time
from typing import Any
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv
from ..graph.state import IncidentState

load_dotenv()

LLM_MODEL = os.getenv("GEMINI_LLM_MODEL")
API_KEY = os.getenv("GEMINI_API_KEY")
BASE_URL = os.getenv("GEMINI_BASE_URL")


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
    llm = ChatOpenAI(
        model=LLM_MODEL,
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=0.1,
    )

    root_cause = state.get("root_cause", "Unknown")
    severity = state.get("severity", "P3")
    blast_radius = state.get("blast_radius", [])
    summaries = state.get("per_service_summaries", {})

    service_summaries = "\n".join(
        f"- {service}: {summary}" for service, summary in summaries.items()
    )
    affected_services = ", ".join(blast_radius) if blast_radius else "none"

    max_retries = 5
    retry_delay = 4  # Start slightly higher for rate limit safety windows

    system_message = SystemMessage(
        content=(
            "You are an expert incident report writer. "
            "Generate a highly professional Markdown incident report and structural corrective steps. "
            "CRITICAL: Your output must be a clean, valid JSON object with precisely two keys: 'incident_report' and 'fix_steps'. "
            "Do not include code block wrap hooks like ```json ... ```. Escaped inner newlines properly."
        )
    )

    human_message = HumanMessage(
        content=(
            "Incident target state specs:\n"
            f"- root_cause: {root_cause}\n"
            f"- severity: {severity}\n"
            f"- affected_services: {affected_services}\n"
            f"- service_summaries:\n{service_summaries}\n\n"
            "Produce structural JSON string formatted exactly like:\n"
            '{\n'
            '  "incident_report": "# Detailed Markdown Report Headings\\n\\nExecutive details go here...",\n'
            '  "fix_steps": ["Actionable step 1", "Actionable step 2"]\n'
            '}\n'
        )
    )

    response = None
    for attempt in range(max_retries):
        try:
            print(f"✍️ [Attempt {attempt + 1}/{max_retries}] Requesting Markdown generation from API... Please wait.")
            import sys; sys.stdout.flush()  # Forces Windows PowerShell to display this string immediately
            
            response = llm.invoke([system_message, human_message]) 
            break
        except Exception as e:
            err_msg = str(e).lower()
            # 1. Handle API Rate Limiting (429) Contexts explicitly
            if "429" in err_msg or "rate" in err_msg:
                cool_down = 20
                print(f"⚠️ API Rate Limited (429). Pausing pipeline execution execution for {cool_down}s to clear tracking window...")
                time.sleep(cool_down)
            # 2. Handle API Overloaded Server Caps (503) Contexts
            elif ("503" in err_msg or "unavailable" in err_msg) and attempt < max_retries - 1:
                print(f"⚠️ API Server Busy (503). Retrying in {retry_delay}s with exponential backoff...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                print(f"❌ Unhandled API Call Exception raised: {e}")
                raise e

    if not response or not hasattr(response, 'content'):
        return {}

    text = response.content.strip()

    # Clean off any markdown wrappers the LLM might have inadvertently appended
    if text.startswith("```json"):
        text = text[7:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        output = json.loads(text)
    except json.JSONDecodeError:
        print("⚠️ Core JSON serialization parse failed due to inner formatting blocks. Dropping to deterministic structural fallbacks.")
        return {}

    if not isinstance(output, dict):
        return {}

    return output


def reporter(state: IncidentState) -> dict[str, Any]:
    print("\n[bold cyan]📋 [Reporter Node Activated][/bold cyan]")
    llm_output = run_reporter_llm(state)

    incident_report = llm_output.get("incident_report", "")
    fix_steps = llm_output.get("fix_steps")

    # Clean Fallback Block if JSON decode completely fell down
    if not incident_report:
        root_cause = state.get("root_cause", "Unknown")
        severity = state.get("severity", "P3")
        blast_radius = state.get("blast_radius", [])
        summaries = state.get("per_service_summaries", {})

        lines: list[str] = [
            f"# Incident Report: {root_cause}",
            "",
            f"**Severity Level:** {severity}",
            "",
            "## Executive Triage Summary",
            "Widespread system microservice degradation observed across cluster interfaces.",
            "",
            "## Impacted Infrastructure Components",
        ]

        if blast_radius:
            lines.extend([f"- **{service}**: Downstream cascade isolation verified." for service in blast_radius])
        else:
            lines.append("- No secondary infrastructure components directly impacted.")

        lines.extend(["", "## Core Log Diagnostic Anomalies"])
        for service, summary in summaries.items():
            lines.append(f"- **{service}**: {summary}")

        lines.extend(["", "## Strategic Remediation Framework Steps"])
        fallback_fix_steps = build_fix_steps(state)
        if fallback_fix_steps:
            lines.extend(
                [f"{idx}. {step}" for idx, step in enumerate(fallback_fix_steps, start=1)]
            )
        else:
            lines.append(
                "1. Manual diagnostic inspection requested. Audit infrastructure log maps."
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