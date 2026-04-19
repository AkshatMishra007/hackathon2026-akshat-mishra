import asyncio
import json
import random
from pathlib import Path
from typing import Any, Dict

from app.config import Settings


class ToolError(RuntimeError):
    pass


class MalformedToolDataError(RuntimeError):
    pass


class DataStore:
    def __init__(self, db_file: str) -> None:
        self._db_path = Path(db_file)
        self._db: Dict[str, Any] = json.loads(self._db_path.read_text(encoding="utf-8"))

    @property
    def db(self) -> Dict[str, Any]:
        return self._db


class ToolSimulator:
    def __init__(self, settings: Settings, datastore: DataStore) -> None:
        self.settings = settings
        self.datastore = datastore

    async def preflight(self, tool_name: str) -> None:
        await asyncio.sleep(
            random.uniform(
                self.settings.min_tool_delay_seconds,
                self.settings.max_tool_delay_seconds,
            )
        )
        if random.random() < self.settings.tool_failure_rate:
            raise ToolError(f"{tool_name}: transient failure")

    def maybe_malformed(self, tool_name: str) -> bool:
        return random.random() < self.settings.malformed_data_rate
