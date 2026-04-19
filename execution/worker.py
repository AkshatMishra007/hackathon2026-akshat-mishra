import asyncio
from typing import List

from agent.decision import DecisionEngine
from agent.orchestrator import AgentOrchestrator
from agent.reasoning import ReasoningEngine
from app.config import Settings
from execution.queue import load_tickets
from models.state import AgentState
from services.llm_service import LLMReasoner
from services.logging_service import LoggingService
from services.retry_service import RetryService
from tools.base import DataStore, ToolSimulator
from tools.comms_tools import CommsTools
from tools.customer_tools import CustomerTools
from tools.kb_tools import KBTools
from tools.order_tools import OrderTools
from tools.product_tools import ProductTools
from tools.refund_tools import RefundTools


def _build_orchestrator(settings: Settings) -> AgentOrchestrator:
    ds = DataStore(settings.db_file)
    sim = ToolSimulator(settings, ds)
    order = OrderTools(sim)
    customer = CustomerTools(sim)
    refund = RefundTools(sim)
    comms = CommsTools(sim)
    product = ProductTools(sim)
    kb = KBTools(sim)

    registry = {
        "get_order": order.get_order,
        "get_customer": customer.get_customer,
        "check_refund_eligibility": refund.check_refund_eligibility,
        "issue_refund": refund.issue_refund,
        "send_reply": comms.send_reply,
        "escalate": comms.escalate,
        "get_product": product.get_product,
        "search_knowledge_base": kb.search_knowledge_base,
    }

    return AgentOrchestrator(
        reasoning_engine=ReasoningEngine(
            llm_reasoner=LLMReasoner(api_key=settings.openai_api_key or settings.gemini_api_key)
        ),
        decision_engine=DecisionEngine(),
        retry_service=RetryService(
            max_attempts=settings.max_tool_retries,
            timeout_s=settings.tool_timeout_seconds,
        ),
        logging_service=LoggingService(settings.logs_dir, settings.audit_rollup_file),
        tool_registry=registry,
        max_steps=settings.max_reasoning_steps,
    )

async def _worker(
    name: str,
    queue: "asyncio.Queue[AgentState | None]",
    orchestrator: AgentOrchestrator,
    results: List[AgentState],
) -> None:
    while True:
        item = await queue.get()
        try:
            if item is None:
                break

            print(f"⚙️ {name} processing {item.ticket.ticket_id}")

            out = await orchestrator.process_ticket(item)
            results.append(out)

        except Exception as e:
            print(f"❌ Error in {name}: {e}")

        finally:
            queue.task_done()


async def run_support_workers(settings: Settings) -> List[AgentState]:
    tickets = load_tickets(settings.ticket_file)
    queue: "asyncio.Queue[AgentState | None]" = asyncio.Queue()
    results: List[AgentState] = []
    orch = _build_orchestrator(settings)

    for t in tickets:
        await queue.put(AgentState(ticket=t))

    workers = [
        asyncio.create_task(_worker(f"worker-{i+1}", queue, orch, results))
        for i in range(settings.max_workers)
    ]
    for _ in workers:
        await queue.put(None)

    await queue.join()
    await asyncio.gather(*workers)

    # Persist one JSON per ticket and aggregate audit log.
    logger = orch.logging_service
    rollup = []
    for state in results:
        payload = logger.write_ticket_log(state)
        rollup.append(payload)
    logger.write_rollup(rollup)
    print(f"Loaded {len(tickets)} tickets")
    return results
