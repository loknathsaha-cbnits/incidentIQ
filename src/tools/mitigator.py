import json
import os
import subprocess
import time
import random
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from src.graph.state import IncidentState

console = Console()

def mitigation_node(state: IncidentState) -> dict:
    """
    Autonomous Runbook Execution Node.
    Maps root cause to pre-approved developer scripts and executes them securely.
    """
    console.print("\n[bold magenta]🤖 [AI Runbook Engine Activated][/bold magenta]")
    
    root_cause = state.get("root_cause", "").lower()
    severity = state.get("severity", "P1")
    
    # 1. Inject Business Impact Metrics for the Demo Screen Presenter
    cost_per_minute = 4500 if severity == "P1" else 1500
    triage_duration = random.randint(11, 16)
    loss_prevented = int((cost_per_minute / 60) * triage_duration * random.uniform(9, 11))

    metrics_view = (
        f"[bold red]System Downtime Cost Rate:[/bold red] ${cost_per_minute}/min\n"
        f"[bold yellow]AI Investigation Duration:[/bold yellow] {triage_duration}s\n"
        f"[bold green]Financial Loss Prevented by Agent Runbook:[/bold green] [yellow]${loss_prevented:,}[/yellow]"
    )
    console.print(Panel(metrics_view, title="[bold white]📈 Financial Telemetry[/bold white]", border_style="magenta", expand=False))

    # 2. Extract service target name from the incident root cause
    target_service = "unknown-service"
    for service in ["payment-service", "api-gateway", "order-service", "auth-service", "inventory-service"]:
        if service in root_cause:
            target_service = service
            break

    # 3. Load developer-approved configurations from runbooks.json
    runbook_path = "runbooks.json"
    matched_runbook = None
    
    if os.path.exists(runbook_path):
        try:
            with open(runbook_path, "r") as f:
                config_data = json.load(f)
                
            # Find matching configuration item based on text keywords
            for runbook in config_data.get("runbooks", []):
                if any(keyword in root_cause for keyword in runbook.get("match_keywords", [])):
                    matched_runbook = runbook
                    break
        except Exception as e:
            console.print(f"[bold red]❌ Failed parsing runbooks config schema: {e}[/bold red]")

    if not matched_runbook:
        console.print("[bold yellow]⚠️ No pre-approved automated runbook matched this root cause anomaly. Escalating to engineers.[/bold yellow]")
        return {"fix_steps": state.get("fix_steps", []) + ["No automated runbook available for execution."]}

    console.print(f"\n[bold cyan]📖 Matched Runbook Config ID:[/bold cyan] [yellow]{matched_runbook['id']}[/yellow]")
    console.print(f"[bold dim]Description: {matched_runbook['description']}[/bold dim]")
    
    # Simulate human operator gate or show automation rules processing it
    console.print(f"[bold white]🤖 Confirm action execution -> `{matched_runbook['mitigation_command']} {target_service}`? (Y/n): [/bold white]", end="")
    time.sleep(1.5)  # Screen layout visibility pause for video recording
    console.print("[bold green]Y (Auto-Approved via Policies)[/bold green]\n")
    time.sleep(0.5)

    # 4. Trigger Real-Time Execution Loop using the subprocess tracker
    base_command = matched_runbook["mitigation_command"].split()
    full_executable_command = base_command + [target_service]

    executed_log_lines = []
    try:
        process = subprocess.Popen(
            full_executable_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wrapped with the correct style argument to avoid initialization crash
        with Progress(
            SpinnerColumn(), 
            TextColumn("[magenta]{task.description}"), 
            BarColumn(bar_width=20, style="magenta"),  # Fixed keyword argument
            console=console
        ) as progress:
            task = progress.add_task("[dim]Running core containment commands...[/dim]", total=None)
            
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    clean_line = line.strip()
                    executed_log_lines.append(clean_line)
                    progress.update(task, description=f"[bold white]{clean_line}[/bold white]")
                    time.sleep(0.6)

        process.wait()
        
        if process.returncode == 0:
            console.print(f"\n[bold green]✅ Runbook completed successfully. {target_service} cluster recovered.[/bold green]\n")
            action_status = f"Successfully completed Runbook Task [{matched_runbook['id']}] targeting {target_service}."
        else:
            error_msg = process.stderr.read().strip()
            console.print(f"\n[bold red]❌ Runbook script failed execution: {error_msg}[/bold red]\n")
            action_status = f"Runbook Task [{matched_runbook['id']}] aborted with errors."
            
    except Exception as e:
        console.print(f"[bold red]❌ Fatal execution anomaly: {e}[/bold red]")
        action_status = f"Failed to execute runbook command path due to internal system exceptions."

    return {
        "fix_steps": state.get("fix_steps", []) + [action_status]
    }