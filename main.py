from src.graph.graph import graph


def create_initial_state() -> dict[str, object]:
    return {
        "scenario": "cascade",
        "logs_dir": "data/logs/",
        "raw_logs": {"payment-service": "ERROR connection pool saturated..."},
        "per_service_summaries": {
            "api-gateway": "errors, warnings observed. Sample events: payment-service latency elevated",
            "frontend": "errors, warnings observed. Sample events: POST /checkout 502 Bad Gateway",
            "notification-service": "Queue depth rising: 340 messages",
            "order-service": "errors, warnings observed. Sample events: POST /orders/confirm waiting",
            "payment-service": "DB connection pool usage high: 20/20 connections in use"
        },
        "root_cause": "payment-service DB connection pool exhaustion",
        "blast_radius": ["api-gateway", "order-service", "notification-service"],
        "severity": "P1",
        "incident_report": """# Incident Report: P1 - Payment Service DB Connection Pool Exhaustion

## Executive Summary
On [Date], a major P1 incident occurred resulting in a complete disruption of the checkout and order confirmation flows. The root cause was identified as database connection pool exhaustion within the `payment-service`. This exhaustion cascaded upstream, causing severe latency in the `order-service` and `api-gateway`, ultimately leading to 502 Bad Gateway errors on the frontend.

## Affected Services
* **payment-service** (Root Cause Resolved)
* **order-service** (Recovering)
* **api-gateway** (Recovering)""",
        "fix_steps": [
            "Increase the maximum database connection pool size for the payment-service to accommodate peak traffic.",
            "Audit and optimize slow-running database queries in the payment-service."
        ],
        "messages": [],
    }


def main() -> None:
    print("Sit back, we are on investigation\n")
    state = create_initial_state()
    
    # This runs your short-circuited graph logic path instantly
    graph.invoke(state)
    
    print("\n🏁 TEST MOCK RUN RUN COMPLETE.")


if __name__ == "__main__":
    main()