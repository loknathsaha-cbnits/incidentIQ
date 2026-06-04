import urllib.request, json, os

from ..graph.state import IncidentState

def github_node(state: IncidentState) -> IncidentState:
    token = os.getenv("GITHUB_TOKEN")
    repo  = os.getenv("GITHUB_REPO")

    issue = {
        "title": f"[{state['severity']}] {state['root_cause']}",
        "body": state["incident_report"],
        "labels": ["incident", state["severity"].lower(), "auto-generated"]
    }

    data = json.dumps(issue).encode()
    req  = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/issues",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json"
        }
    )
    with urllib.request.urlopen(req) as res:
        result = json.loads(res.read())
        state["github_issue_url"] = result["html_url"]

    return state