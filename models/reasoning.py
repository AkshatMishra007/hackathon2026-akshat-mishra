from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ReasoningStep:
    thought: str
    action: str
    action_input: Dict[str, Any]
