# 🚨 IncidentIQ

> An AI-powered production incident triage workflow that analyzes service logs, identifies probable root causes, determines incident severity and blast radius, generates an incident report with remediation steps, and automatically creates a GitHub issue for high-severity incidents.

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-Agentic_Workflow-orange.svg)
![LLM](https://img.shields.io/badge/LLM-OpenAI--Compatible-green.svg)
![Status](https://img.shields.io/badge/Status-POC-yellow.svg)

## What It Does

IncidentIQ is a LangGraph-based incident investigation workflow designed to reduce the manual effort involved in analyzing production failures.

The workflow reads service log files and processes them through a sequence of AI-powered and deterministic steps to:

* Parse production service logs
* Identify relevant `WARN`, `ERROR`, and `FATAL` events
* Summarize failures for individual services
* Identify a probable root service and root cause
* Determine the affected services / blast radius
* Classify the incident as **P1, P2, or P3**
* Generate a structured Markdown incident report
* Generate ordered remediation steps
* Automatically create a GitHub issue for P1/P2 incidents
* Display the investigation results in the terminal
* Send the incident report by email

The current POC operates on log files stored in `data/logs/`.

---

# Tech Stack

| Component                     | Technology                                                          |
| ----------------------------- | ------------------------------------------------------------------- |
| **Language**                  | Python 3.12+                                                        |
| **Workflow Orchestration**    | LangGraph                                                           |
| **LLM Integration**           | LangChain `ChatOpenAI`                                              |
| **LLM Provider**              | OpenAI-compatible endpoint configured through environment variables |
| **State Management**          | LangGraph `TypedDict` state                                         |
| **Environment Configuration** | python-dotenv                                                       |
| **Terminal UI**               | Rich                                                                |
| **Issue Management**          | GitHub REST API                                                     |
| **Email Notifications**       | Gmail SMTP                                                          |
| **Input Data**                | Production-style `.log` files                                       |

The project requires Python 3.12+ and currently declares `langgraph`, `langchain-core`, `langchain-openai`, `python-dotenv`, `rich`, and `faker` as dependencies.

---

# Quick Start

## 1. Clone the Repository

```bash
git clone https://github.com/loknathsaha-cbnits/incidentIQ.git
cd incidentIQ
```

[IncidentIQ repository](https://github.com/loknathsaha-cbnits/incidentIQ?utm_source=chatgpt.com)

## 2. Create a Virtual Environment

Python **3.12 or later** is required.

```bash
python -m venv .venv
```

### Windows

```bash
.venv\Scripts\activate
```

### Linux / macOS

```bash
source .venv/bin/activate
```

## 3. Install Dependencies

Using `pip`:

```bash
pip install -e .
```

Or, if `uv` is being used:

```bash
pip install uv
uv sync
```

The repository contains both `pyproject.toml` and `uv.lock`.

---

# Configuration

Create a `.env` file in the project root.

The application currently reads the following environment variables:

```env
# LLM configuration
GROK_LLM_MODEL=your-model-name
GROK_API_KEY=your-api-key
GROK_BASE_URL=your-openai-compatible-base-url

# Reporter LLM configuration
GEMINI_LLM_MODEL=your-model-name
GEMINI_API_KEY=your-api-key
GEMINI_BASE_URL=your-openai-compatible-base-url

# GitHub
GITHUB_TOKEN=your-github-token
GITHUB_REPO=owner/repository

# Email
GMAIL_ADDRESS=your-email@gmail.com
GMAIL_APP_PASSWORD=your-gmail-app-password
NOTIFY_EMAIL=recipient@example.com
```

The incident analysis node reads the `GROK_*` variables, while the report-generation node reads the `GEMINI_*` variables. Both are accessed through LangChain's `ChatOpenAI` interface.

GitHub issue creation uses `GITHUB_TOKEN` and `GITHUB_REPO`.

Email notification uses `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, and `NOTIFY_EMAIL`.

> **Important:** The variable names above reflect the current source code. They should be kept consistent with the implementation unless the configuration code is changed.

---

# How It Works

The workflow is implemented using a LangGraph `StateGraph` with a shared `IncidentState`.

```text
                         Production Logs
                              │
                              ▼
                    ┌──────────────────┐
                    │    Log Reader    │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Incident Analysis│
                    │      Agent       │
                    └────────┬─────────┘
                             │
                 ┌───────────┴───────────┐
                 │                       │
                 ▼                       ▼
             Root Cause             Blast Radius
                 │                       │
                 └───────────┬───────────┘
                             ▼
                         Severity
                             │
                             ▼
                    ┌──────────────────┐
                    │     Reporter     │
                    └────────┬─────────┘
                             │
                             ▼
                        Decision
                       /         \
                      /           \
                 P1 / P2           P3
                    │               │
                    ▼               ▼
             GitHub Issue          END
                    │
                    ▼
                 Display
                    │
                    ▼
                 Email
                    │
                    ▼
                   END
```

The actual graph is:

```text
START
  │
  ▼
log_reader
  │
  ▼
agent
  │
  ▼
reporter
  │
  ▼
decision
  │
  ├── P1/P2 ──► github_node ──► display ──► emailer ──► END
  │
  └── P3 ────────────────────────────────────────────► END
```

This routing is defined directly in `src/graph/graph.py`.

---

# Incident State

All nodes communicate through a shared `IncidentState`.

```text
IncidentState
│
├── scenario
├── logs_dir
├── raw_logs
├── per_service_summaries
├── root_cause
├── blast_radius
├── severity
├── incident_report
├── fix_steps
├── messages
├── next_action
├── github_issue_url
└── email_sent
```

This state acts as the contract between the different stages of the workflow.

---

# 1. Log Reader

The first node reads `.log` files from:

```text
data/logs/
```

Each log line is expected to follow this format:

```text
[TIMESTAMP] LEVEL SERVICE MESSAGE
```

For example:

```text
[2026-08-01 10:15:20] ERROR payment-service Failed to acquire DB connection
```

The parser extracts:

* Timestamp
* Log level
* Service
* Message

Only significant events are considered for incident analysis. `WARN`, `ERROR`, and `FATAL` levels are treated as relevant, along with messages containing keywords such as:

```text
timeout
failed
unavailable
degraded
critical
health check
circuit breaker
exhausted
out of memory
refused
```

The node also creates per-service summaries and initially classifies the overall scenario as `healthy`, `partial`, or `cascade`.

---

# 2. Incident Analysis Agent

The `agent` node performs the main incident analysis.

The parsed service information is summarized and sent to an LLM through LangChain's `ChatOpenAI`.

The model is instructed to return structured JSON containing:

```json
{
  "root_service": "...",
  "root_cause": "...",
  "blast_radius": [],
  "severity": "P1"
}
```

The analysis is constrained to the evidence supplied by the logs.

The resulting information is used to determine:

### Root Service

The service believed to be responsible for the incident.

### Root Cause

The probable underlying failure.

### Blast Radius

Other services that are affected by the root failure.

### Severity

One of:

```text
P1
P2
P3
```

---

# Root Cause Fallback

A deterministic fallback is also present.

If the LLM does not return usable root-cause information, the implementation checks the parsed logs for known patterns.

For example, messages containing:

```text
connection pool
pool exhausted
failed to acquire db connection
```

can result in:

```text
payment-service DB connection pool exhaustion
```

The implementation also contains pattern-based blast-radius detection for services such as:

* `api-gateway`
* `frontend`
* `order-service`
* `notification-service`

This provides a fallback when the LLM response cannot be parsed successfully.

---

# Severity Classification

Severity is determined during the analysis stage.

The current implementation follows rules such as:

```text
FATAL event + unknown root service
        │
        ▼
       P1

Known root service + affected services
        │
        ▼
       P1

ERROR events
        │
        ▼
       P2

Otherwise
        │
        ▼
       P3
```

The resulting severity controls whether a GitHub issue is created.

---

# 3. Incident Reporter

After analysis, the `reporter` node generates the incident report.

The report-generation LLM receives:

* Root cause
* Severity
* Affected services
* Per-service summaries

It is instructed to return:

```json
{
  "incident_report": "...",
  "fix_steps": [
    "...",
    "..."
  ]
}
```

The incident report is generated in Markdown format.

If the LLM report generation fails, a deterministic fallback report is created containing:

```text
Incident Report
Severity
Root Cause
Affected Services
Service Summaries
Recommended Fix Steps
```

---

# Fix Steps

The fallback remediation logic currently focuses on the payment-service scenario.

Typical generated steps include:

1. Confirm payment-service health and database connectivity.
2. Inspect the payment-service database connection pool.
3. Restart or scale the connection pool if necessary.
4. Reset API gateway circuit breakers when affected.
5. Validate frontend checkout traffic.
6. Clear order-service backlog when affected.
7. Verify notification-service recovery.
8. Escalate to database/platform engineers for unresolved P1 incidents.
9. Monitor the end-to-end flow until recovery.

The steps are stored in `IncidentState.fix_steps`.

---

# 4. Conditional Decision

After the incident report is generated, the `decision` node determines the next action.

```text
Severity
   │
   ├── P1 ──► Create GitHub Issue
   │
   ├── P2 ──► Create GitHub Issue
   │
   └── P3 ──► End
```

This routing is implemented using LangGraph conditional edges.

---

# 5. GitHub Issue Creation

For P1 and P2 incidents, the `github_node` automatically creates a GitHub issue.

The issue contains:

```text
Title:
[P1] <root cause>

Labels:
incident
p1
auto-generated
```

The generated incident report is placed in the issue body.

The GitHub API response is then used to store the resulting issue URL in:

```python
github_issue_url
```

The GitHub repository is configured through:

```env
GITHUB_REPO=owner/repository
```

and authentication is performed with:

```env
GITHUB_TOKEN=your-token
```

---

# 6. Terminal Display

The `display` node presents the investigation results using Rich.

It displays:

* Incident detection status
* Service health summary
* Incident severity
* Incident report
* Fix steps
* GitHub issue URL when created
* Investigation completion status

A short progress animation is also shown while the results are being displayed.

---

# 7. Email Notification

The final notification stage sends the incident information through Gmail SMTP.

The email contains:

* Severity
* Root cause
* Blast radius
* Incident report
* Fix steps
* GitHub issue URL

The email is sent using:

```text
smtp.gmail.com
```

Port `465` with SSL is attempted first, with port `587` and STARTTLS used as a fallback.

The result is stored in:

```python
email_sent
```

---

# Sample Incident Flow

A typical investigation can be visualized as:

```text
Production Logs
      │
      ▼
Payment Service
"Failed to acquire DB connection"
      │
      ▼
Log Reader
      │
      ▼
Incident Analysis
      │
      ├── Root Service:
      │      payment-service
      │
      ├── Root Cause:
      │      DB connection pool exhaustion
      │
      ├── Blast Radius:
      │      api-gateway
      │      order-service
      │
      └── Severity:
             P1
              │
              ▼
       Incident Reporter
              │
              ├── Incident Report
              └── Fix Steps
              │
              ▼
       GitHub Issue Created
              │
              ▼
          Terminal Display
              │
              ▼
         Email Notification
```

---

# Project Structure

```text
incidentIQ/
│
├── data/
│   └── logs/
│       └── *.log
│
├── src/
│   ├── graph/
│   │   ├── graph.py
│   │   ├── state.py
│   │   └── __init__.py
│   │
│   ├── tools/
│   │   ├── agent.py
│   │   ├── display.py
│   │   ├── emailer.py
│   │   ├── github_node.py
│   │   ├── log_reader.py
│   │   ├── reporter.py
│   │   └── __init__.py
│   │
│   └── __init__.py
│
├── scripts/
│
├── debug_email.py
├── main.py
├── script.py
├── pyproject.toml
├── uv.lock
└── README.md
```

The repository currently contains the graph/state implementation under `src/graph`, the workflow nodes under `src/tools`, and sample incident logs under `data/logs`.

---

# Running the Application

Once the environment has been configured:

```bash
python main.py
```

The application initializes the initial incident state and invokes the compiled LangGraph workflow.

The final incident report and remediation steps are printed after the workflow completes.

The initial state contains fields such as:

```text
scenario
logs_dir
raw_logs
per_service_summaries
root_cause
blast_radius
severity
incident_report
fix_steps
messages
```

---

# Adding New Incident Scenarios

New log scenarios can be added under:

```text
data/logs/
```

The log reader automatically scans the directory for `.log` files.

For a new incident type, the workflow can be extended by updating:

* Root-cause detection patterns
* Blast-radius patterns
* Severity rules
* Recommended remediation steps

The current deterministic fallback logic contains several patterns specifically related to payment-service/database failures, so broader incident coverage would require extending these rules.

---

# Current Limitations

This project is currently a **proof of concept**.

Important implementation considerations:

* Logs are currently read from the local `data/logs/` directory.
* There is no live monitoring or production log-stream integration.
* Root-cause analysis is LLM-assisted but also contains hardcoded fallback rules.
* Some remediation logic is specifically tailored to payment-service/database scenarios.
* GitHub issue creation occurs only for P1/P2 incidents.
* The email stage is only reached after the GitHub issue path; P3 incidents end directly after the decision node.
* LLM provider configuration is environment-based and requires compatible API endpoints.
* The application currently runs as a command-line workflow rather than a continuously running incident-management service.
* The current LangGraph workflow is a fixed graph; the LLM performs incident analysis within the graph rather than dynamically controlling the graph's execution path.

---

# Architecture Summary

```text
                  ┌───────────────────┐
                  │  Production Logs  │
                  └─────────┬─────────┘
                            │
                            ▼
                  ┌───────────────────┐
                  │    Log Reader     │
                  │  Parse & Filter   │
                  └─────────┬─────────┘
                            │
                            ▼
                  ┌───────────────────┐
                  │ Incident Analysis │
                  │       LLM         │
                  └─────────┬─────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
          Root Cause    Blast Radius   Severity
              │             │             │
              └─────────────┼─────────────┘
                            ▼
                  ┌───────────────────┐
                  │ Incident Reporter │
                  │       LLM         │
                  └─────────┬─────────┘
                            │
                            ▼
                       ┌─────────┐
                       │Decision │
                       └────┬────┘
                            │
                  ┌─────────┴─────────┐
                  │                   │
               P1 / P2                P3
                  │                   │
                  ▼                   ▼
           GitHub Issue              END
                  │
                  ▼
               Display
                  │
                  ▼
                Email
                  │
                  ▼
                 END
```

IncidentIQ combines **LangGraph orchestration, LLM-based incident analysis, deterministic log processing and fallback logic, automated GitHub issue creation, terminal reporting, and email notification** into a single incident-triage workflow.

---

## Repository

[IncidentIQ on GitHub](https://github.com/loknathsaha-cbnits/incidentIQ?utm_source=chatgpt.com)
