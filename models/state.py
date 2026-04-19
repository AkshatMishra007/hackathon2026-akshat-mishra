from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from models.ticket import Ticket


@dataclass
class AuditEvent:
    timestamp: str
    event_type: str
    content: Dict[str, Any]


@dataclass
class AgentState:
    ticket: Ticket
    step_count: int = 0
    observations: Dict[str, Any] = field(default_factory=dict)
    thoughts: List[str] = field(default_factory=list)
    tool_history: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    failed_actions: List[str] = field(default_factory=list)
    audit_trail: List[AuditEvent] = field(default_factory=list)
    final_decision: Optional[Dict[str, Any]] = None
    dead_letter: bool = False

    def log_event(self, event_type: str, content: Dict[str, Any]) -> None:
        self.audit_trail.append(
            AuditEvent(
                timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                event_type=event_type,
                content=content,
            )
        )