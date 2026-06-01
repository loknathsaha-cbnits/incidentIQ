from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..graph.state import IncidentState

LOG_LINE_RE = re.compile(r"^\[(?P<timestamp>[^\]]+)\]\s+(?P<level>\w+)\s+(?P<service>[^\s]+)\s+(?P<message>.+)$")
RELEVANT_LEVELS = {"WARN", "ERROR", "FATAL"}


def parse_log_line(line: str) -> dict[str, str] | None:
    match = LOG_LINE_RE.match(line.strip())
    if not match:
        return None
    return match.groupdict()


def is_relevant(entry: dict[str, str]) -> bool:
    message = entry["message"].lower()
    if entry["level"] in RELEVANT_LEVELS:
        return True
    return any(
        keyword in message
        for keyword in (
            "timeout",
            "failed",
            "unavailable",
            "degraded",
            "critical",
            "health check",
            "circuit breaker",
            "exhausted",
            "outofmemory",
            "out of memory",
            "refused",
        )
    )


def summarize_entries(entries: list[dict[str, str]]) -> str:
    if not entries:
        return "No significant incidents found in this service."

    counts = {"WARN": 0, "ERROR": 0, "FATAL": 0}
    for entry in entries:
        if entry["level"] in counts:
            counts[entry["level"]] += 1

    summary_parts = [f"{counts[level]} {level.lower()}" for level in ("FATAL", "ERROR", "WARN") if counts[level]]
    sample_messages = [entry["message"] for entry in entries[:3]]
    return f"{', '.join(summary_parts)} detected. Key events: {'; '.join(sample_messages)}."


def infer_scenario(parsed: dict[str, list[dict[str, str]]]) -> str:
    impacted = [service for service, entries in parsed.items() if any(is_relevant(entry) for entry in entries)]
    if not impacted:
        return "healthy"
    if len(impacted) >= 4:
        return "cascade"
    return "partial"


def log_reader(state: IncidentState) -> dict[str, Any]:
    print("Log reader started")
    logs_dir = Path(__file__).resolve().parents[2] / "data" / "logs"
    raw_logs: dict[str, str] = {}
    parsed_logs: dict[str, list[dict[str, str]]] = {}
    per_service_summaries: dict[str, str] = {}

    if not logs_dir.exists():
        raise FileNotFoundError(f"Log directory not found: {logs_dir}")

    for log_path in sorted(logs_dir.glob("*.log")):
        text = log_path.read_text(encoding="utf-8")
        raw_logs[log_path.stem] = text
        entries = [entry for entry in (parse_log_line(line) for line in text.splitlines()) if entry]
        parsed_logs[log_path.stem] = entries
        filtered = [entry for entry in entries if is_relevant(entry)]
        per_service_summaries[log_path.stem] = summarize_entries(filtered)

    scenario = infer_scenario(parsed_logs)

    return {
        "scenario": scenario,
        "logs_dir": str(logs_dir),
        "raw_logs": raw_logs,
        "per_service_summaries": per_service_summaries,
        "root_cause": "",
        "blast_radius": [],
        "severity": "P3",
        "incident_report": "",
        "fix_steps": [],
        "messages": [],
    }