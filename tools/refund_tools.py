from typing import Any, Dict

from tools.base import MalformedToolDataError, ToolSimulator


class RefundTools:
    def __init__(self, simulator: ToolSimulator) -> None:
        self.simulator = simulator

    async def check_refund_eligibility(self, order_id: str, category: str = "refund_request") -> Dict[str, Any]:
        await self.simulator.preflight("check_refund_eligibility")
        order = self.simulator.datastore.db.get("orders", {}).get(order_id)
        policy = self.simulator.datastore.db.get("refund_policy", {})
        if self.simulator.maybe_malformed("check_refund_eligibility"):
            raise MalformedToolDataError("eligibility payload malformed")
        if not order:
            return {"eligible": False, "reason": "order_missing"}

        default_days = 14 if category == "refund_request" else 7
        if category == "refund_request":
            max_days = int(policy.get("refund_window_days", default_days))
            if order.get("status") not in {"delivered", "lost"}:
                return {"eligible": False, "reason": "order_not_in_eligible_status"}
        else:
            max_days = int(policy.get("damaged_wrong_window_days", default_days))
            if order.get("status") != "delivered":
                return {"eligible": False, "reason": "order_not_delivered"}

        within_window = order.get("days_since_delivery", 999) <= max_days
        if within_window and not order.get("already_refunded", False):
            return {"eligible": True, "reason": "within_policy"}
        return {"eligible": False, "reason": "outside_policy_or_refunded"}

    async def issue_refund(self, order_id: str, amount: float) -> Dict[str, Any]:
        await self.simulator.preflight("issue_refund")
        order = self.simulator.datastore.db.get("orders", {}).get(order_id)
        if not order:
            return {"ok": False, "reason": "order_missing"}
        if order.get("already_refunded", False):
            return {"ok": False, "reason": "already_refunded", "order_id": order_id}
        if amount <= 0:
            return {"ok": False, "reason": "invalid_amount", "order_id": order_id}
        order["already_refunded"] = True
        return {"ok": True, "order_id": order_id, "amount": round(float(amount), 2), "status": "refunded"}
