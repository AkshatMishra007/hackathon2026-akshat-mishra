from typing import Any, Dict

from tools.base import MalformedToolDataError, ToolSimulator


class OrderTools:
    def __init__(self, simulator: ToolSimulator) -> None:
        self.simulator = simulator

    async def get_order(self, order_id: str) -> Dict[str, Any]:
        await self.simulator.preflight("get_order")
        order = self.simulator.datastore.db.get("orders", {}).get(order_id)
        if self.simulator.maybe_malformed("get_order"):
            raise MalformedToolDataError("get_order returned malformed payload")
        if not order:
            return {"found": False, "order_id": order_id}
        return {"found": True, **order}
