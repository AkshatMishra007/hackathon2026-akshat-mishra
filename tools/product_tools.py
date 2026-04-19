from typing import Any, Dict

from tools.base import MalformedToolDataError, ToolSimulator


class ProductTools:
    def __init__(self, simulator: ToolSimulator) -> None:
        self.simulator = simulator

    async def get_product(self, product_id: str) -> Dict[str, Any]:
        await self.simulator.preflight("get_product")
        product = self.simulator.datastore.db.get("products", {}).get(product_id)
        if self.simulator.maybe_malformed("get_product"):
            raise MalformedToolDataError("get_product malformed")
        if not product:
            return {"found": False, "product_id": product_id}
        return {"found": True, **product}
