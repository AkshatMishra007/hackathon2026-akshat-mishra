from dataclasses import dataclass
from typing import Any, Dict

from models.state import AgentState


@dataclass
class Decision:
    decision_type: str
    confidence: float
    payload: Dict[str, Any]


class DecisionEngine:
    def decide(self, state: AgentState) -> Decision:
        t = state.ticket
        order = state.observations.get("order", {})
        customer = state.observations.get("customer", {})
        eligibility = state.observations.get("refund_eligibility", {})
        if not eligibility:
            # Backward-compatible read for older logs/state snapshots.
            eligibility = state.observations.get("check_refund_eligibility", {})

        base = 0.55 + (0.1 if customer.get("segment") == "vip" else 0.0)

        escalation_flags = [
            t.priority_hint == "high",
            t.category in {"legal", "fraud_claim", "chargeback"},
            "manager" in t.message.lower(),
            order.get("status") == "lost",
            state.errors.count("malformed_data") > 0,
            not order.get("found", True),  # Missing order
        ]
        if any(escalation_flags):
            return Decision(
                decision_type="escalate",
                confidence=min(0.96, base + 0.25),
                payload={
                    "summary": f"Escalate {t.ticket_id} due to risk/uncertainty; include full audit trail.",
                    "priority": "high" if t.priority_hint == "high" else "normal",
                },
            )

        if eligibility.get("eligible") and t.category in {"refund_request", "damaged_item", "wrong_item"}:
            amount = float(t.requested_amount or order.get("total_amount", 0.0))
            return Decision(
                decision_type="refund",
                confidence=min(0.98, base + 0.3),
                payload={
                    "order_id": t.order_id,
                    "amount": round(amount, 2),
                    "reason": eligibility.get("reason", "within_policy"),
                },
            )

        return Decision(
            decision_type="reply",
            confidence=min(0.9, base + 0.15),
            payload={
                "message": "Thanks for reaching out. We reviewed your case and shared the next best resolution.",
            },
        )
