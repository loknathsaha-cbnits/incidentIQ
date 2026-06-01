from src.graph.graph import graph


def create_initial_state() -> dict[str, object]:
    return {
        "scenario": "",
        "logs_dir": "",
        "raw_logs": {},
        "per_service_summaries": {},
        "root_cause": "",
        "blast_radius": [],
        "severity": "P3",
        "incident_report": "",
        "fix_steps": [],
        "messages": [],
    }


def main() -> None:
    print("Sit back, we are on investigation")
    state = create_initial_state()
    result = graph.invoke(state)
    print(result.get("incident_report", "No report generated."))
    print("\n---\n")
    print("Fix steps:")
    for step in result.get("fix_steps", []):
        print(f"- {step}")


if __name__ == "__main__":
    main()
