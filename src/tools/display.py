from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
import time

from ..graph.state import IncidentState

console = Console()


def display(state: IncidentState) -> IncidentState:
    """
    Renders the final, high-impact triage and remediation overview to the console.
    Converts raw AI markdown text into beautifully styled terminal widgets.
    """
    
    # ── Chronological Loading Ticker ─────────────────────────────────────
    # Simulates final log compilation and dashboard rendering
    steps = [
        "Synthesizing root cause artifacts...",
        "Validating runbook patch status...",
        "Compiling cross-service telemetry...",
        "Rendering final incident report dashboard..."
    ]

    with Progress(
            SpinnerColumn(), 
            TextColumn("[magenta]{task.description}"), 
            BarColumn(bar_width=20, style="magenta"),  # Changed 'color' to 'style'
            console=console
        ) as progress:
        task = progress.add_task("", total=len(steps))
        for step in steps:
            progress.update(task, description=step)
            time.sleep(0.6)   # Paced cleanly for screen recorders
            progress.advance(task)

    # ── Global Screen Heading Separator ──────────────────────────────────
    console.rule("[bold red]🚨 SYSTEM TRIAGE & AUTO-REMEDIATION METRICS[/bold red]")
    console.print()

    # ── Dynamic Service Status Table ─────────────────────────────────────
    table = Table(box=box.ROUNDED, title="🔍 Post-Mitigation Service Cluster Health")
    table.add_column("Service Component", style="cyan", no_wrap=True)
    table.add_column("Remediation Status", style="bold", no_wrap=True)
    table.add_column("Observed Diagnostics Anomaly (Truncated)")

    severity_colors = {
        "HEALTHY / MUTATED": "green", 
        "CRITICAL EFFECTED": "red", 
        "DEGRADED": "yellow", 
        "HEALTHY": "green"
    }

    root_cause = state.get("root_cause", "").lower()

    for service, summary in state["per_service_summaries"].items():
        # Determine current state context dynamically
        if service in root_cause:
            # If the service was the root cause, highlight that the AI fixed/mutated it
            status = "HEALTHY / MUTATED"
        elif service in state["blast_radius"]:
            # Services knocked out downstream in the cascade collapse
            status = "CRITICAL EFFECTED"
        else:
            status = "HEALTHY"
            
        color = severity_colors.get(status, "white")
        table.add_row(
            service,
            f"[{color}]{status}[/{color}]",
            summary[:90] # Safe text bounding truncation
        )

    console.print(table)
    console.print()

    # ── Rich Markdown Incident Report Panel (The Main Content Block) ─────
    # Crucial Fix: Wrapping raw text strings inside Markdown() yields premium styling
    raw_markdown_report = state.get("incident_report", "### No Analytical Text Payload Found.")
    formatted_markdown = Markdown(raw_markdown_report)

    console.print(Panel(
        formatted_markdown,
        title=f"[bold red]⚠ SYSTEM LEVEL INCIDENT OVERVIEW — {state.get('severity', 'P1')}[/bold red]",
        border_style="red",
        padding=(1, 2),
    ))

    # ── Executed Script Actions / Fix Steps Summary ──────────────────────
    console.print("\n[bold yellow]🛠 Actionable Remediation Event History Log:[/bold yellow]")
    for i, step in enumerate(state.get("fix_steps", []), 1):
        console.print(f"  [magenta]{i}.[/magenta] {step}")

    console.print()

    # ── GitHub Issue Tracking Panel ──────────────────────────────────────
    if state.get("github_issue_url"):
        issue_info = (
            f"[bold white]Issue Target URL:[/bold white] [cyan underline]{state['github_issue_url']}[/cyan underline]\n"
            f"[dim]Tracking item dispatched synchronously to repository. Logs preserved upstream.[/dim]"
        )
        console.print(Panel(
            issue_info,
            title="[bold green]✅ GitHub Operational Escalation Issue Dispatched[/bold green]",
            border_style="green",
            padding=(1, 2),
            expand=False
        ))

    console.print()
    console.rule("[bold green]🏁 COMPREHENSIVE TRIAGE AND MITIGATION FLOW COMPLETE[/bold green]")
    console.print()

    return state