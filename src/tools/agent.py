from __future__ import annotations
import os
import json
import re
from typing import Any
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from ..graph.state import IncidentState

load_dotenv()

LLM_MODEL = os.getenv("GROK_LLM_MODEL")
API_KEY=os.getenv("GROK_API_KEY")
BASE_URL=os.getenv("GROK_BASE_URL")

def parse_raw_logs(raw_logs: dict[str, str]) -> dict[str, list[dict[str, str]]]:
    pattern = re.compile(
        r"^\[(?P<timestamp>[^\]]+)\]\s+(?P<level>\w+)\s+(?P<service>[^\s]+)\s+(?P<message>.+)$"
    )
    parsed: dict[str, list[dict[str, str]]] = {}

    for service, text in raw_logs.items():
        entries: list[dict[str, str]] = []
        for line in text.splitlines():
            match = pattern.match(line.strip())
            if match:
                entries.append(match.groupdict())
        parsed[service] = entries

    return parsed


def run_agent_llm(parsed: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    print("Agent thinking")
    llm = ChatOpenAI(
    model = LLM_MODEL,
    api_key = API_KEY,
    base_url = BASE_URL,
    temperature= 0.1,
    )
    service_summaries: list[str] = []

    for service, entries in parsed.items():
        if not entries:
            continue

        relevant = [entry for entry in entries if entry["level"] in {"WARN", "ERROR", "FATAL"}]
        summary = f"{service}: {len(relevant)} relevant entries"
        sample_messages = "; ".join(entry["message"] for entry in relevant[:3])
        if sample_messages:
            summary += f" | samples: {sample_messages}"
        service_summaries.append(summary)

    system_message = SystemMessage(
        content=(
            "You are an incident analysis assistant. "
            "Analyze parsed service log entries and return a JSON object with exactly these fields:\n"
            "- root_service: string\n"
            "- root_cause: string\n"
            "- blast_radius: list of service names\n"
            "- severity: P1, P2, or P3\n\n"
            "Use only the evidence provided. Do not include any extra text outside valid JSON."
        )
    )

    human_message = HumanMessage(
        content=(
            "Parsed service log summaries:\n"
            + "\n".join(service_summaries)
            + "\n\nRespond with valid JSON only."
        )
    )

    print("Contacting Groq API for log analysis... Please wait.")
    response = llm.invoke([system_message, human_message])
    content = response.content.strip()

    try:
        output = json.loads(content)
    except json.JSONDecodeError:
        # fallback to heuristic extraction if the LLM did not return valid JSON
        return {
            "root_service": "unknown",
            "root_cause": "Unable to determine the root cause from LLM output.",
            "blast_radius": [],
            "severity": "P3",
        }

    if not all(key in output for key in ("root_service", "root_cause", "blast_radius", "severity")):
        return {
            "root_service": output.get("root_service", "unknown"),
            "root_cause": output.get("root_cause", "Unable to determine the root cause from LLM output."),
            "blast_radius": output.get("blast_radius", []),
            "severity": output.get("severity", "P3"),
        }

    return output


def detect_root_cause(parsed: dict[str, list[dict[str, str]]]) -> tuple[str, str]:
    payment_entries = parsed.get("payment-service", [])
    for entry in payment_entries:
        message = entry["message"].lower()
        if "connection pool" in message or "pool exhausted" in message or "failed to acquire db connection" in message:
            return (
                "payment-service",
                "payment-service DB connection pool exhaustion and failed database acquisitions",
            )
        if "hikari" in message or "db session" in message:
            return (
                "payment-service",
                "payment-service cannot obtain database connections from the pool, causing transaction failures",
            )

    for service, entries in parsed.items():
        for entry in entries:
            message = entry["message"].lower()
            if "health check failed" in message and "payment-service" in message:
                return (
                    "payment-service",
                    "payment-service is failing health checks and rejecting downstream traffic",
                )

    return ("unknown", "Unable to determine the root cause from logs. Review service logs for more detail.")


def build_blast_radius(parsed: dict[str, list[dict[str, str]]], root_service: str) -> list[str]:
    blast: set[str] = set()
    service_patterns = {
        "frontend": ["502", "504", "upstream timeout", "error rate spike", "checkout"],
        "api-gateway": ["timeout", "circuit breaker", "health check failed", "503", "service unavailable", "thread pool"],
        "order-service": ["payment-service call timeout", "pending order backlog", "stuck in pending"],
        "notification-service": ["queue depth", "smtp connection refused", "outofmemory", "out of memory", "worker thread crashed"],
    }

    for service, entries in parsed.items():
        if service == root_service:
            continue
        for entry in entries:
            message = entry["message"].lower()
            if entry["level"] in {"WARN", "ERROR", "FATAL"}:
                if service == "api-gateway" and "payment-service" in message:
                    blast.add(service)
                    break
                if any(token in message for token in service_patterns.get(service, [])):
                    blast.add(service)
                    break
    return sorted(blast)


def summarize_service(entries: list[dict[str, str]]) -> str:
    if not entries:
        return "No incident-level activity detected."

    levels = [entry["level"] for entry in entries]
    tags: list[str] = []
    if "FATAL" in levels:
        tags.append("fatal errors")
    if "ERROR" in levels:
        tags.append("errors")
    if "WARN" in levels:
        tags.append("warnings")

    sample_messages = [entry["message"] for entry in entries[:2]]
    return f"{', '.join(tags)} observed. Sample events: {'; '.join(sample_messages)}"


def agent(state: IncidentState) -> dict[str, Any]:
    print("Agent node running")
    raw_logs = state.get("raw_logs", {})
    parsed = parse_raw_logs(raw_logs)

    llm_output = run_agent_llm(parsed)
    root_service = llm_output.get("root_service", "unknown")
    root_cause = llm_output.get("root_cause", "")
    blast_radius = llm_output.get("blast_radius", [])

    if not root_cause or root_service == "unknown":
        root_service, root_cause = detect_root_cause(parsed)
    if not blast_radius:
        blast_radius = build_blast_radius(parsed, root_service)

    if root_service == "unknown" and any(
        entry["level"] == "FATAL" for entries in parsed.values() for entry in entries
    ):
        severity = "P1"
    elif root_service != "unknown" and len(blast_radius) >= 1:
        severity = "P1"
    elif any(entry["level"] == "ERROR" for entries in parsed.values() for entry in entries):
        severity = "P2"
    else:
        severity = "P3"

    per_service_summaries: dict[str, str] = {}
    for service, entries in parsed.items():
        relevant = [entry for entry in entries if entry["level"] in {"WARN", "ERROR", "FATAL"}]
        per_service_summaries[service] = summarize_service(relevant)

    return {
        "per_service_summaries": per_service_summaries,
        "root_cause": root_cause,
        "blast_radius": blast_radius,
        "severity": severity,
        "incident_report": state.get("incident_report", ""),
        "fix_steps": state.get("fix_steps", []),
        "messages": state.get("messages", []),
    }