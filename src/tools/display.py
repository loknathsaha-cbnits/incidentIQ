from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel

from ..graph.state import IncidentState

console = Console()

def display(state: IncidentState) -> IncidentState:
    # Service status table
    table = Table(box=box.ROUNDED, title="🔍 Service Health Summary")
    table.add_column("Service",  style="cyan")
    table.add_column("Status",   style="bold")
    table.add_column("Summary")

    severity_colors = {"CRITICAL": "red", "DEGRADED": "yellow", "HEALTHY": "green"}

    for service, summary in state["per_service_summaries"].items():
        status = "CRITICAL" if service in state["blast_radius"] else "HEALTHY"
        color  = severity_colors[status]
        table.add_row(service, f"[{color}]{status}[/{color}]", summary[:80])

    console.print(table)

    # Incident report panel
    console.print(Panel(
        state["incident_report"],
        title=f"[red]⚠ INCIDENT REPORT — {state['severity']}[/red]",
        border_style="red"
    ))

    # Fix steps
    console.print("\n[bold yellow]🛠  Fix Steps (in order):[/bold yellow]")
    for i, step in enumerate(state["fix_steps"], 1):
        console.print(f"  {i}. {step}")

    # GitHub issue link
    if state.get("github_issue_url"):
        console.print(f"\n[bold green]✅ GitHub Issue Created:[/bold green] {state['github_issue_url']}\n")

    return state