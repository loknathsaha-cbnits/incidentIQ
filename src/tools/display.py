from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
import time

from ..graph.state import IncidentState

console = Console()


def display(state: IncidentState) -> IncidentState:

    # ── Loading animation ────────────────────────────────────────────────
    steps = [
        "Reading service logs...",
        "Correlating failures across services...",
        "Identifying root cause...",
        "Calculating blast radius...",
        "Generating incident report...",
    ]

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold yellow]{task.description}"),
        transient=True,   # clears itself after done — clean terminal
        console=console,
    ) as progress:
        task = progress.add_task("", total=len(steps))
        for step in steps:
            progress.update(task, description=step)
            time.sleep(0.8)   # purely for visual effect on camera
            progress.advance(task)

    # ── Separator ────────────────────────────────────────────────────────
    console.rule("[bold red]⚠  INCIDENT DETECTED[/bold red]")
    console.print()

    # ── Service status table ─────────────────────────────────────────────
    table = Table(box=box.ROUNDED, title="🔍 Service Health Summary")
    table.add_column("Service",  style="cyan",  no_wrap=True)
    table.add_column("Status",   style="bold",  no_wrap=True)
    table.add_column("Summary")

    severity_colors = {"CRITICAL": "red", "DEGRADED": "yellow", "HEALTHY": "green"}

    for service, summary in state["per_service_summaries"].items():
        status = "CRITICAL" if service in state["blast_radius"] else "HEALTHY"
        color  = severity_colors.get(status, "white")
        table.add_row(
            service,
            f"[{color}]{status}[/{color}]",
            summary[:80]
        )

    console.print(table)
    console.print()

    # ── Incident report panel ────────────────────────────────────────────
    console.print(Panel(
        state["incident_report"],
        title=f"[red]⚠  INCIDENT REPORT — {state['severity']}[/red]",
        border_style="red",
        padding=(1, 2),
    ))

    # ── Fix steps ────────────────────────────────────────────────────────
    console.print("\n[bold yellow]🛠  Fix Steps (in order):[/bold yellow]")
    for i, step in enumerate(state["fix_steps"], 1):
        console.print(f"  [cyan]{i}.[/cyan] {step}")

    console.print()

    # ── GitHub issue link ────────────────────────────────────────────────
    if state.get("github_issue_url"):
        console.print(Panel(
            f"[bold white]{state['github_issue_url']}[/bold white]",
            title="[green]✅ GitHub Issue Auto-Created[/green]",
            border_style="green",
            padding=(0, 2),
        ))

    console.print()
    console.rule("[bold green]✅  Triage Complete[/bold green]")

    return state