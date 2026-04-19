import json
import sys
from pathlib import Path


REQUIRED_FILES = [
    "README.md",
    "architecture.png",
    "failure_modes.md",
    "audit_log.json",
]


def _fail(msg: str) -> int:
    print(f"[FAIL] {msg}")
    return 1


def _ok(msg: str) -> None:
    print(f"[OK]   {msg}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]

    for rel in REQUIRED_FILES:
        path = root / rel
        if not path.exists():
            return _fail(f"Missing required file: {rel}")
        _ok(f"Found required file: {rel}")

    audit_path = root / "audit_log.json"
    try:
        payload = json.loads(audit_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return _fail(f"Cannot parse audit_log.json: {exc}")

    if not isinstance(payload, list):
        return _fail("audit_log.json must be a JSON array")
    if len(payload) != 20:
        return _fail(f"audit_log.json must contain 20 ticket entries, got {len(payload)}")

    ticket_ids = {
        entry.get("ticket_id")
        for entry in payload
        if isinstance(entry, dict) and isinstance(entry.get("ticket_id"), str)
    }
    if len(ticket_ids) != 20:
        return _fail(f"audit_log.json must include 20 unique ticket_ids, got {len(ticket_ids)}")
    _ok("audit_log.json contains 20 unique ticket entries")

    decisions = {"refund": 0, "reply": 0, "escalate": 0}
    for entry in payload:
        decision = ((entry or {}).get("final_decision") or {}).get("decision")
        if decision in decisions:
            decisions[decision] += 1
    _ok(f"Decision distribution: {decisions}")

    print("Submission verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
