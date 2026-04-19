from typing import Dict

from tools.base import ToolSimulator


class CommsTools:
    def __init__(self, simulator: ToolSimulator) -> None:
        self.simulator = simulator

    async def send_reply(self, ticket_id: str, message: str) -> Dict[str, str | bool]:
        await self.simulator.preflight("send_reply")
        return {"ok": True, "ticket_id": ticket_id, "message": message}

    async def escalate(self, ticket_id: str, summary: str, priority: str) -> Dict[str, str | bool]:
        await self.simulator.preflight("escalate")
        return {"ok": True, "ticket_id": ticket_id, "summary": summary, "priority": priority}
