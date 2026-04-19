import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from models.state import AgentState


class LoggingService:
    def __init__(self, logs_dir: str, audit_rollup_file: str) -> None:
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.audit_rollup_file = Path(audit_rollup_file)

    def write_ticket_log(self, state: AgentState) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "ticket_id": state.ticket.ticket_id,
            "step_count": state.step_count,
            "observations": state.observations,
            "thoughts": state.thoughts,
            "tool_history": state.tool_history,
            "errors": state.errors,
            "final_decision": state.final_decision,
            "dead_letter": state.dead_letter,
            "audit_trail": [asdict(a) for a in state.audit_trail],
        }
        out_file = self.logs_dir / f"{state.ticket.ticket_id}.json"
        out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    def write_rollup(self, all_ticket_logs: List[Dict[str, Any]]) -> None:
        self.audit_rollup_file.write_text(json.dumps(all_ticket_logs, indent=2), encoding="utf-8")

    def write_dead_letter(self, state: AgentState) -> None:
        dead_letter_file = self.logs_dir / "dead_letter_queue.jsonl"
        entry = {
            "ticket_id": state.ticket.ticket_id,
            "errors": state.errors,
            "final_decision": state.final_decision,
            "dead_letter": state.dead_letter,
        }
        with dead_letter_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
