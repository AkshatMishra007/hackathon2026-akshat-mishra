from typing import Any, Dict

from tools.base import MalformedToolDataError, ToolSimulator


class CustomerTools:
    def __init__(self, simulator: ToolSimulator) -> None:
        self.simulator = simulator

    async def get_customer(self, email: str) -> Dict[str, Any]:
        await self.simulator.preflight("get_customer")
        customer = self.simulator.datastore.db.get("customers", {}).get(email)
        if self.simulator.maybe_malformed("get_customer"):
            raise MalformedToolDataError("get_customer returned malformed payload")
        if not customer:
            return {"found": False, "email": email, "segment": "unknown"}
        return {"found": True, **customer}
