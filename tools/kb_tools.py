from typing import Any, Dict, List

from tools.base import MalformedToolDataError, ToolSimulator


class KBTools:
    def __init__(self, simulator: ToolSimulator) -> None:
        self.simulator = simulator

    async def search_knowledge_base(self, query: str) -> Dict[str, Any]:
        await self.simulator.preflight("search_knowledge_base")
        kb: List[Dict[str, Any]] = self.simulator.datastore.db.get("knowledge_base", [])
        if self.simulator.maybe_malformed("search_knowledge_base"):
            raise MalformedToolDataError("search_knowledge_base malformed")
        query_l = query.lower()
        hits = [row for row in kb if any(token in row["text"].lower() for token in query_l.split()[:5])]
        return {"query": query, "hits": hits[:3]}
