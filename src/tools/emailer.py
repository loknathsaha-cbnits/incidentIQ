import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from rich.console import Console
from dotenv import load_dotenv

from ..graph.state import IncidentState

load_dotenv()   # ← make sure .env is loaded inside the node too

console = Console()


def emailer(state: IncidentState) -> IncidentState:

    sender       = os.getenv("GMAIL_ADDRESS")
    app_password = os.getenv("GMAIL_APP_PASSWORD")
    recipient    = os.getenv("NOTIFY_EMAIL", sender)

    # ── Debug: confirm env vars loaded ──────────────────────────────────
    print(f"DEBUG sender      : {sender}")
    print(f"DEBUG recipient   : {recipient}")
    print(f"DEBUG password set: {'YES' if app_password else 'NO'}")
    print(f"DEBUG password len: {len(app_password) if app_password else 0}")

    subject = f"[{state['severity']}] Incident Detected — {state['root_cause'][:60]}"
    fix_steps_text = "\n".join(
        f"  {i}. {step}" for i, step in enumerate(state["fix_steps"], 1)
    )

    # ── Build plain text ─────────────────────────────────────────────────
    text_body = f"""
INCIDENT REPORT — {state['severity']}

ROOT CAUSE: {state['root_cause']}
BLAST RADIUS: {', '.join(state['blast_radius'])}

{state['incident_report']}

FIX STEPS:
{fix_steps_text}

GitHub Issue: {state.get('github_issue_url', 'N/A')}
    """.strip()

    # ── Build HTML ───────────────────────────────────────────────────────
    html_body = f"""
<html><body style="font-family: monospace; padding: 20px;">
  <h2 style="color: red;">⚠ INCIDENT REPORT — {state['severity']}</h2>
  <p><b>Root Cause:</b> {state['root_cause']}</p>
  <p><b>Blast Radius:</b> {', '.join(state['blast_radius'])}</p>
  <hr/>
  <pre>{state['incident_report']}</pre>
  <hr/>
  <b>🛠 Fix Steps:</b>
  <ol>{''.join(f"<li>{step}</li>" for step in state['fix_steps'])}</ol>
  <hr/>
  <p>🔗 <b>GitHub Issue:</b>
    <a href="{state.get('github_issue_url', '#')}">{state.get('github_issue_url', 'Not created')}</a>
  </p>
  <small style="color: grey;">Sent automatically by IncidentIQ Agent</small>
</body></html>
    """

    # ── Assemble message ─────────────────────────────────────────────────
    msg = MIMEMultipart("alternative")
    msg["From"]    = sender
    msg["To"]      = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    # ── Actually send it ─────────────────────────────────────────────────
    try:
        print("DEBUG [1] Connecting to smtp.gmail.com:465 ...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            print("DEBUG [2] Connected ✓")
            server.login(sender, app_password)
            print("DEBUG [3] Logged in ✓")
            server.sendmail(sender, recipient, msg.as_string())
            print("DEBUG [4] sendmail() called ✓")

        state["email_sent"] = True
        console.print(f"\n[bold green]📧 Email sent to:[/bold green] {recipient}\n")

    except smtplib.SMTPAuthenticationError:
        state["email_sent"] = False
        console.print("\n[bold red]❌ AUTH FAILED — wrong app password or 2FA not enabled[/bold red]\n")

    except smtplib.SMTPConnectError:
        state["email_sent"] = False
        console.print("\n[bold red]❌ CONNECT FAILED — port 465 blocked, trying 587...[/bold red]\n")
        # ── Fallback to port 587 ─────────────────────────────────────────
        try:
            print("DEBUG [1b] Trying port 587 ...")
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.ehlo()
                server.starttls()
                server.login(sender, app_password)
                server.sendmail(sender, recipient, msg.as_string())
                print("DEBUG [2b] Sent via port 587 ✓")
            state["email_sent"] = True
            console.print(f"\n[bold green]📧 Email sent (587) to:[/bold green] {recipient}\n")
        except Exception as e2:
            console.print(f"\n[bold red]❌ Port 587 also failed:[/bold red] {type(e2).__name__}: {e2}\n")

    except Exception as e:
        state["email_sent"] = False
        console.print(f"\n[bold red]❌ Unexpected error:[/bold red] {type(e).__name__}: {e}\n")
        raise e   # surface it fully in the terminal

    return state