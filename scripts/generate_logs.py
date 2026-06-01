"""
generate_logs.py

Run this script to generate synthetic logs for all 5 services.
It simulates a real 2 AM incident: a DB connection pool exhaustion
in the payment service that cascades across the entire system.

Usage:
    uv run scripts/generate_logs.py
    uv run scripts/generate_logs.py --scenario healthy     # all services fine
    uv run scripts/generate_logs.py --scenario cascade     # default: the incident
    uv run scripts/generate_logs.py --scenario partial     # only 2 services affected
"""

import argparse
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

# ── Output directory ────────────────────────────────────────────────────────
LOGS_DIR = Path(__file__).parent.parent / "data" / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ── Helpers ──────────────────────────────────────────────────────────────────

def ts(base: datetime, offset_seconds: int = 0) -> str:
    """Return an ISO-style log timestamp."""
    return (base + timedelta(seconds=offset_seconds)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def write_log(service: str, lines: list[str]) -> Path:
    path = LOGS_DIR / f"{service}.log"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  ✓  {path.relative_to(Path.cwd())}  ({len(lines)} lines)")
    return path


# ── Per-service log generators ───────────────────────────────────────────────

def gen_frontend(base: datetime, scenario: str) -> list[str]:
    lines = []
    # Normal traffic before incident
    for i in range(20):
        lines.append(f"[{ts(base, i*30)}] INFO  frontend        GET /dashboard 200 34ms user_id=u{random.randint(100,999)}")
        lines.append(f"[{ts(base, i*30+10)}] INFO  frontend        GET /api/orders 200 45ms user_id=u{random.randint(100,999)}")

    if scenario in ("cascade", "partial"):
        # 2 AM — users start seeing errors because payment is broken
        incident_start = 600
        lines.append(f"[{ts(base, incident_start)}]  WARN  frontend        POST /checkout 502 Bad Gateway — upstream timeout user_id=u882")
        lines.append(f"[{ts(base, incident_start+15)}] ERROR frontend        POST /checkout 502 Bad Gateway — upstream timeout user_id=u441")
        lines.append(f"[{ts(base, incident_start+20)}] ERROR frontend        POST /checkout 502 Bad Gateway — upstream timeout user_id=u237")
        lines.append(f"[{ts(base, incident_start+30)}] ERROR frontend        POST /checkout 504 Gateway Timeout user_id=u991")
        lines.append(f"[{ts(base, incident_start+45)}] ERROR frontend        POST /checkout 504 Gateway Timeout user_id=u102")
        lines.append(f"[{ts(base, incident_start+60)}]  WARN  frontend        Retry attempt 1/3 for POST /checkout user_id=u882")
        lines.append(f"[{ts(base, incident_start+90)}] ERROR frontend        Retry attempt 3/3 FAILED for POST /checkout — giving up user_id=u882")
        lines.append(f"[{ts(base, incident_start+95)}]  WARN  frontend        Error rate spike detected: 78% of /checkout requests failing")
        for i in range(5):
            lines.append(f"[{ts(base, incident_start+100+i*20)}] ERROR frontend        POST /checkout 502 Bad Gateway user_id=u{random.randint(100,999)}")

    return lines


def gen_api_gateway(base: datetime, scenario: str) -> list[str]:
    lines = []
    for i in range(15):
        lines.append(f"[{ts(base, i*40)}] INFO  api-gateway     Routed POST /checkout → payment-service 200 OK latency=42ms")
        lines.append(f"[{ts(base, i*40+5)}] INFO  api-gateway     Routed GET  /orders   → order-service   200 OK latency=18ms")

    if scenario in ("cascade", "partial"):
        incident_start = 590
        lines.append(f"[{ts(base, incident_start)}]  WARN  api-gateway     payment-service latency elevated: 1800ms (threshold: 500ms)")
        lines.append(f"[{ts(base, incident_start+10)}]  WARN  api-gateway     payment-service latency elevated: 3200ms")
        lines.append(f"[{ts(base, incident_start+20)}] ERROR api-gateway     payment-service health check FAILED — marking unhealthy")
        lines.append(f"[{ts(base, incident_start+25)}] ERROR api-gateway     Routed POST /checkout → payment-service TIMEOUT after 5000ms")
        lines.append(f"[{ts(base, incident_start+30)}] ERROR api-gateway     Routed POST /checkout → payment-service TIMEOUT after 5000ms")
        lines.append(f"[{ts(base, incident_start+35)}]  WARN  api-gateway     Circuit breaker OPEN for payment-service (5 failures in 30s)")
        lines.append(f"[{ts(base, incident_start+40)}] ERROR api-gateway     All requests to payment-service being rejected (circuit OPEN)")
        lines.append(f"[{ts(base, incident_start+60)}]  WARN  api-gateway     Thread pool saturation: 94/100 worker threads busy")
        lines.append(f"[{ts(base, incident_start+75)}] ERROR api-gateway     Thread pool EXHAUSTED — dropping incoming requests")
        lines.append(f"[{ts(base, incident_start+90)}] ERROR api-gateway     503 Service Unavailable returned to 12 clients in last 10s")

    return lines


def gen_payment_service(base: datetime, scenario: str) -> list[str]:
    """This is the ROOT CAUSE service."""
    lines = []
    for i in range(10):
        lines.append(f"[{ts(base, i*60)}] INFO  payment-service Processed payment txn_id=txn_{random.randint(10000,99999)} amount=£{random.uniform(10,500):.2f} status=SUCCESS")

    if scenario in ("cascade", "partial"):
        incident_start = 540  # starts slightly BEFORE others — root cause
        lines.append(f"[{ts(base, incident_start)}]  WARN  payment-service DB connection pool usage high: 18/20 connections in use")
        lines.append(f"[{ts(base, incident_start+10)}]  WARN  payment-service DB connection pool usage critical: 20/20 connections in use")
        lines.append(f"[{ts(base, incident_start+20)}] ERROR payment-service Failed to acquire DB connection — pool exhausted (timeout=3000ms)")
        lines.append(f"[{ts(base, incident_start+21)}] ERROR payment-service Failed to acquire DB connection — pool exhausted (timeout=3000ms)")
        lines.append(f"[{ts(base, incident_start+22)}] ERROR payment-service Failed to acquire DB connection — pool exhausted (timeout=3000ms)")
        lines.append(f"[{ts(base, incident_start+23)}] ERROR payment-service com.zaxxer.hikari.pool.HikariPool - Connection is not available, request timed out after 3000ms")
        lines.append(f"[{ts(base, incident_start+25)}] ERROR payment-service Transaction FAILED txn_id=txn_83821 — could not open DB session")
        lines.append(f"[{ts(base, incident_start+30)}] ERROR payment-service Transaction FAILED txn_id=txn_83822 — could not open DB session")
        lines.append(f"[{ts(base, incident_start+35)}] ERROR payment-service Transaction FAILED txn_id=txn_83823 — could not open DB session")
        lines.append(f"[{ts(base, incident_start+40)}] FATAL payment-service Unhandled exception: NullPointerException at PaymentProcessor.java:142")
        lines.append(f"[{ts(base, incident_start+41)}] FATAL payment-service   at DBConnectionManager.getConnection(DBConnectionManager.java:87)")
        lines.append(f"[{ts(base, incident_start+42)}] FATAL payment-service   at PaymentProcessor.processTransaction(PaymentProcessor.java:142)")
        lines.append(f"[{ts(base, incident_start+43)}] FATAL payment-service   at CheckoutController.handleRequest(CheckoutController.java:56)")
        lines.append(f"[{ts(base, incident_start+50)}] FATAL payment-service Service health degraded — 100% of last 10 transactions failed")
        lines.append(f"[{ts(base, incident_start+55)}]  WARN  payment-service Attempting DB connection pool reset...")
        lines.append(f"[{ts(base, incident_start+120)}] ERROR payment-service DB connection pool reset FAILED — DB host still unreachable")

    return lines


def gen_order_service(base: datetime, scenario: str) -> list[str]:
    lines = []
    for i in range(12):
        lines.append(f"[{ts(base, i*50)}] INFO  order-service   Created order order_id=ord_{random.randint(5000,9999)} items=3 status=PENDING")
        lines.append(f"[{ts(base, i*50+10)}] INFO  order-service   Sent order confirmation event to notification-service order_id=ord_{random.randint(5000,9999)}")

    if scenario == "cascade":
        incident_start = 620
        lines.append(f"[{ts(base, incident_start)}]  WARN  order-service   POST /orders/confirm waiting on payment-service response... (2100ms)")
        lines.append(f"[{ts(base, incident_start+15)}]  WARN  order-service   POST /orders/confirm waiting on payment-service response... (4300ms)")
        lines.append(f"[{ts(base, incident_start+30)}] ERROR order-service   payment-service call TIMEOUT after 5000ms — order ord_7823 stuck in PENDING")
        lines.append(f"[{ts(base, incident_start+31)}] ERROR order-service   payment-service call TIMEOUT after 5000ms — order ord_7824 stuck in PENDING")
        lines.append(f"[{ts(base, incident_start+45)}]  WARN  order-service   Pending order backlog growing: 14 orders awaiting payment confirmation")
        lines.append(f"[{ts(base, incident_start+90)}]  WARN  order-service   Pending order backlog growing: 47 orders awaiting payment confirmation")
        lines.append(f"[{ts(base, incident_start+120)}] ERROR order-service   Pending order backlog CRITICAL: 103 orders — SLA breach imminent")

    return lines


def gen_notification_service(base: datetime, scenario: str) -> list[str]:
    lines = []
    for i in range(10):
        lines.append(f"[{ts(base, i*60)}] INFO  notification    Sent email order_id=ord_{random.randint(5000,9999)} template=order_confirmation to=user{random.randint(1,99)}@example.com status=DELIVERED")

    if scenario == "cascade":
        incident_start = 650
        lines.append(f"[{ts(base, incident_start)}] INFO  notification    Queue depth: 8 messages (normal)")
        lines.append(f"[{ts(base, incident_start+30)}]  WARN  notification    Queue depth rising: 340 messages — consumers may be slow")
        lines.append(f"[{ts(base, incident_start+60)}]  WARN  notification    Queue depth: 1,820 messages — investigate order-service publish rate")
        lines.append(f"[{ts(base, incident_start+90)}] ERROR notification    Queue depth CRITICAL: 8,400 messages — consumer throughput insufficient")
        lines.append(f"[{ts(base, incident_start+100)}] ERROR notification    Failed to send email — SMTP connection refused (too many open connections)")
        lines.append(f"[{ts(base, incident_start+105)}] ERROR notification    Failed to send email — SMTP connection refused")
        lines.append(f"[{ts(base, incident_start+110)}] ERROR notification    Failed to send email — SMTP connection refused")
        lines.append(f"[{ts(base, incident_start+120)}] FATAL notification    Worker thread crashed: OutOfMemoryError — queue buffer exceeded heap limit")
        lines.append(f"[{ts(base, incident_start+121)}] FATAL notification    Worker thread crashed: OutOfMemoryError")
        lines.append(f"[{ts(base, incident_start+125)}] FATAL notification    All 4 consumer threads DOWN — queue processing HALTED")
        lines.append(f"[{ts(base, incident_start+130)}] ERROR notification    Service effectively dead — no messages being processed")

    return lines


# ── Entrypoint ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic service logs")
    parser.add_argument(
        "--scenario",
        choices=["healthy", "cascade", "partial"],
        default="cascade",
        help="Incident scenario to simulate (default: cascade)",
    )
    args = parser.parse_args()

    # Simulate 2 AM incident — logs start ~10 min before
    base_time = datetime(2025, 6, 1, 1, 50, 0)

    print(f"\n🔧  Generating logs — scenario: [{args.scenario}]\n")

    write_log("frontend",             gen_frontend(base_time, args.scenario))
    write_log("api-gateway",          gen_api_gateway(base_time, args.scenario))
    write_log("payment-service",      gen_payment_service(base_time, args.scenario))
    write_log("order-service",        gen_order_service(base_time, args.scenario))
    write_log("notification-service", gen_notification_service(base_time, args.scenario))

    print(f"\n✅  All logs written to: data/logs/\n")
    print("Next step → uv run main.py\n")


if __name__ == "__main__":
    main()
