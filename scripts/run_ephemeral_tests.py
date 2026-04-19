import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path


TEST_DECISION_ENGINE = """
import unittest
from agent.decision import DecisionEngine
from models.state import AgentState
from models.ticket import Ticket


class DecisionEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = DecisionEngine()

    def _state(self, category: str = "refund_request", priority: str = "normal") -> AgentState:
        ticket = Ticket(
            ticket_id="T-1",
            order_id="ORD-1",
            customer_email="u@example.com",
            category=category,
            subject="s",
            message="m",
            requested_amount=20.0,
            priority_hint=priority,
        )
        return AgentState(ticket=ticket)

    def test_refund_decision_when_eligible(self) -> None:
        state = self._state(category="refund_request")
        state.observations["order"] = {"status": "delivered", "total_amount": 20.0}
        state.observations["customer"] = {"segment": "regular"}
        state.observations["refund_eligibility"] = {"eligible": True, "reason": "within_policy"}
        decision = self.engine.decide(state)
        self.assertEqual(decision.decision_type, "refund")

    def test_escalate_for_high_priority(self) -> None:
        state = self._state(category="delivery_issue", priority="high")
        state.observations["order"] = {"status": "delivered"}
        state.observations["customer"] = {"segment": "regular"}
        state.observations["refund_eligibility"] = {"eligible": False, "reason": "n/a"}
        decision = self.engine.decide(state)
        self.assertEqual(decision.decision_type, "escalate")
"""

TEST_ORCHESTRATOR = """
import asyncio
import collections
import tempfile
import unittest
from pathlib import Path

from agent.decision import DecisionEngine
from agent.orchestrator import AgentOrchestrator
from agent.reasoning import ReasoningEngine
from app.config import Settings
from models.state import AgentState
from models.ticket import Ticket
from services.logging_service import LoggingService
from services.retry_service import RetryService
from tools.base import DataStore, ToolSimulator
from tools.comms_tools import CommsTools
from tools.customer_tools import CustomerTools
from tools.kb_tools import KBTools
from tools.order_tools import OrderTools
from tools.product_tools import ProductTools
from tools.refund_tools import RefundTools


class OrchestratorTests(unittest.TestCase):
    def test_process_ticket_completes_with_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path.cwd()
            settings = Settings(
                db_file=str(root / "data" / "mock_db.json"),
                tool_failure_rate=0.0,
                malformed_data_rate=0.0,
                min_tool_delay_seconds=0.0,
                max_tool_delay_seconds=0.0,
                logs_dir=temp_dir,
                audit_rollup_file=str(Path(temp_dir) / "audit.json"),
            )
            ds = DataStore(settings.db_file)
            sim = ToolSimulator(settings, ds)
            registry = {
                "get_order": OrderTools(sim).get_order,
                "get_customer": CustomerTools(sim).get_customer,
                "check_refund_eligibility": RefundTools(sim).check_refund_eligibility,
                "issue_refund": RefundTools(sim).issue_refund,
                "send_reply": CommsTools(sim).send_reply,
                "escalate": CommsTools(sim).escalate,
                "get_product": ProductTools(sim).get_product,
                "search_knowledge_base": KBTools(sim).search_knowledge_base,
            }
            orchestrator = AgentOrchestrator(
                reasoning_engine=ReasoningEngine(llm_reasoner=None),
                decision_engine=DecisionEngine(),
                retry_service=RetryService(max_attempts=1, timeout_s=1.0),
                logging_service=LoggingService(settings.logs_dir, settings.audit_rollup_file),
                tool_registry=registry,
                max_steps=6,
            )
            state = AgentState(
                ticket=Ticket(
                    ticket_id="T-1001",
                    order_id="ORD-001",
                    customer_email="alice@example.com",
                    category="refund_request",
                    subject="refund",
                    message="damaged item",
                    requested_amount=20.0,
                    product_id="PRD-101",
                )
            )
            out = asyncio.run(orchestrator.process_ticket(state))
            self.assertIsNotNone(out.final_decision)
            self.assertGreaterEqual(len(out.tool_history), 3)
            # Regression guard: no infinite-like repeated eligibility loop.
            action_counts = collections.Counter(h.get("action") for h in out.tool_history if isinstance(h, dict))
            self.assertLessEqual(action_counts.get("check_refund_eligibility", 0), 2)

    def test_refund_tool_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path.cwd()
            settings = Settings(
                db_file=str(root / "data" / "mock_db.json"),
                tool_failure_rate=0.0,
                malformed_data_rate=0.0,
                min_tool_delay_seconds=0.0,
                max_tool_delay_seconds=0.0,
                logs_dir=temp_dir,
                audit_rollup_file=str(Path(temp_dir) / "audit.json"),
            )
            ds = DataStore(settings.db_file)
            sim = ToolSimulator(settings, ds)
            refund_tool = RefundTools(sim)
            first = asyncio.run(refund_tool.issue_refund("ORD-001", 10.0))
            second = asyncio.run(refund_tool.issue_refund("ORD-001", 10.0))
            self.assertTrue(first.get("ok"))
            self.assertFalse(second.get("ok"))
            self.assertEqual(second.get("reason"), "already_refunded")
"""

TEST_WORKER = """
import asyncio
import tempfile
import unittest
from pathlib import Path

from app.config import Settings
from execution.worker import run_support_workers


class WorkerIntegrationTests(unittest.TestCase):
    def test_full_run_outputs_20_tickets(self) -> None:
        root = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                ticket_file=str(root / "data" / "tickets.json"),
                db_file=str(root / "data" / "mock_db.json"),
                logs_dir=temp_dir,
                audit_rollup_file=str(Path(temp_dir) / "audit_log.json"),
                max_workers=3,
                tool_failure_rate=0.0,
                malformed_data_rate=0.0,
                min_tool_delay_seconds=0.0,
                max_tool_delay_seconds=0.0,
                max_tool_retries=1,
                tool_timeout_seconds=1.0,
            )
            result = asyncio.run(run_support_workers(settings))
            self.assertEqual(len(result), 22)

    def test_full_run_has_at_least_one_refund_and_no_eligibility_spam(self) -> None:
        root = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                ticket_file=str(root / "data" / "tickets.json"),
                db_file=str(root / "data" / "mock_db.json"),
                logs_dir=temp_dir,
                audit_rollup_file=str(Path(temp_dir) / "audit_log.json"),
                max_workers=3,
                tool_failure_rate=0.0,
                malformed_data_rate=0.0,
                min_tool_delay_seconds=0.0,
                max_tool_delay_seconds=0.0,
                max_tool_retries=1,
                tool_timeout_seconds=1.0,
            )
            result = asyncio.run(run_support_workers(settings))
            refunds = [r for r in result if (r.final_decision or {}).get("decision") == "refund"]
            self.assertGreaterEqual(len(refunds), 1)
            for state in result:
                actions = [h.get("action") for h in state.tool_history if isinstance(h, dict)]
                self.assertLessEqual(actions.count("check_refund_eligibility"), 2)
"""


def _write_temp_tests(temp_tests_dir: Path) -> None:
    files = {
        "test_decision_engine.py": TEST_DECISION_ENGINE,
        "test_orchestrator.py": TEST_ORCHESTRATOR,
        "test_worker_integration.py": TEST_WORKER,
    }
    for name, content in files.items():
        (temp_tests_dir / name).write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="ephemeral-tests-") as tmp:
        temp_tests_dir = Path(tmp)
        _write_temp_tests(temp_tests_dir)
        cmd = [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            str(temp_tests_dir),
            "-p",
            "test_*.py",
        ]
        completed = subprocess.run(cmd, cwd=root, check=False)
        return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
