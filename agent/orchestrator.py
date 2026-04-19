import asyncio
import time
from typing import Any, Awaitable, Callable, Dict

from agent.decision import DecisionEngine
from agent.reasoning import ReasoningEngine
from models.state import AgentState
from services.logging_service import LoggingService
from services.retry_service import RetryService
from tools.base import MalformedToolDataError
from utils.validators import ValidationError, validate_decision_payload, validate_tool_observation


# Central mapping for tool outputs (removes hardcoding)
TOOL_OUTPUT_MAP = {
    "get_order": "order",
    "get_customer": "customer",
    "get_product": "product",
    "search_knowledge_base": "kb",
    "check_refund_eligibility": "refund_eligibility",
}


class AgentOrchestrator:
    def __init__(
        self,
        reasoning_engine: ReasoningEngine,
        decision_engine: DecisionEngine,
        retry_service: RetryService,
        logging_service: LoggingService,
        tool_registry: Dict[str, Callable[..., Awaitable[Dict[str, Any]]]],
        max_steps: int = 6,
    ) -> None:
        self.reasoning_engine = reasoning_engine
        self.decision_engine = decision_engine
        self.retry_service = retry_service
        self.logging_service = logging_service
        self.tool_registry = tool_registry
        self.max_steps = max_steps

        # Decision handlers
        self.handlers = {
            "refund": self._handle_refund,
            "escalate": self._handle_escalate,
            "reply": self._handle_reply,
        }

    async def process_ticket(self, state: AgentState) -> AgentState:
        state.log_event("ticket_received", {"ticket_id": state.ticket.ticket_id})

        while state.step_count < self.max_steps:
            step = self.reasoning_engine.next_step(state)
            if not step:
                break

            state.step_count += 1
            state.thoughts.append(step.thought)
            state.log_event("thought", {"thought": step.thought})

            tool_fn = self.tool_registry.get(step.action)
            if not tool_fn:
                err = f"unknown_tool:{step.action}"
                state.errors.append(err)
                state.log_event("error", {"message": err})
                break

            try:
                start_time = time.time()

                result = await self.retry_service.run(tool_fn, **step.action_input)
                validate_tool_observation(step.action, result)

                latency = time.time() - start_time

                key = TOOL_OUTPUT_MAP.get(step.action, step.action)
                state.observations[key] = result

                state.tool_history.append({
                    "action": step.action,
                    "input": step.action_input,
                    "output": result,
                    "latency": latency,
                })

                state.log_event("action", {
                    "name": step.action,
                    "input": step.action_input,
                    "output": result,
                    "latency": latency,
                })

            except MalformedToolDataError as exc:
                state.errors.append("malformed_data")
                state.failed_actions.append(step.action)  
                state.log_event("error", {"message": str(exc)})

            except ValidationError as exc:
                err = f"validation_error:{step.action}:{exc}"
                state.errors.append(err)
                state.failed_actions.append(step.action)   
                state.log_event("error", {"message": err})

            except Exception as exc:
                err = f"tool_failure:{step.action}:{exc}"
                state.errors.append(err)
                state.log_event("error", {"message": err})

            # Circuit breaker
            if len(state.errors) >= 3:
                state.log_event("circuit_break", {"reason": "too_many_errors"})
                break

        # Decision phase
        decision = self.decision_engine.decide(state)
        state.final_decision = {
            "decision": decision.decision_type,
            "confidence": decision.confidence,
            "payload": decision.payload,
        }

        try:
            validate_decision_payload(decision.decision_type, decision.payload)
        except ValidationError as exc:
            state.dead_letter = True
            err = f"validation_error:decision:{exc}"
            state.errors.append(err)
            state.log_event("dead_letter", {"reason": err})
            self.logging_service.write_dead_letter(state)
            return state

        state.log_event("decision", state.final_decision)

        try:
            handler = self.handlers.get(decision.decision_type)
            if handler:
                await handler(state)
        except Exception as exc:
            action_name = getattr(step, "action", "unknown")
            err = f"tool_failure:{action_name}:{exc}"
            state.errors.append(err)
            state.failed_actions.append(action_name)
            state.log_event("error", {"message": err})

        return state

    # =========================
    # HANDLERS (CLEAN DESIGN)
    # =========================

    async def _handle_refund(self, state: AgentState) -> None:
        decision = state.final_decision
        ticket = state.ticket
        p = decision["payload"]

        # Re-check eligibility (safety gate)
        eligibility = await self.retry_service.run(
            self.tool_registry["check_refund_eligibility"],
            order_id=p["order_id"],
            category=ticket.category,
        )

        if not eligibility.get("eligible"):
            await self._fallback_escalation(
                state,
                f"Refund blocked for {ticket.ticket_id}: eligibility failed at execution.",
            )
            return

        result = await self.retry_service.run(
            self.tool_registry["issue_refund"],
            order_id=p["order_id"],
            amount=p["amount"],
        )

        if not result.get("ok"):
            await self._fallback_escalation(
                state,
                f"Refund failed: {result.get('reason', 'unknown')}",
            )
            return

        reply = f"Refund of ${p['amount']:.2f} has been issued."
        await self._send_reply(state, reply)

    async def _handle_escalate(self, state: AgentState) -> None:
        p = state.final_decision["payload"]
        ticket = state.ticket

        result = await self.retry_service.run(
            self.tool_registry["escalate"],
            ticket_id=ticket.ticket_id,
            summary=p["summary"],
            priority=p["priority"],
        )

        state.tool_history.append({"action": "escalate", "output": result})
        state.log_event("action", {"name": "escalate", "output": result})

    async def _handle_reply(self, state: AgentState) -> None:
        message = state.final_decision["payload"].get(
            "message", "Thank you for contacting support."
        )
        await self._send_reply(state, message)

    async def _send_reply(self, state: AgentState, message: str) -> None:
        ticket = state.ticket

        result = await self.retry_service.run(
            self.tool_registry["send_reply"],
            ticket_id=ticket.ticket_id,
            message=message,
        )

        state.tool_history.append({"action": "send_reply", "output": result})
        state.log_event("action", {"name": "send_reply", "output": result})

    async def _fallback_escalation(self, state: AgentState, reason: str) -> None:
        ticket = state.ticket

        fallback = {
            "decision": "escalate",
            "confidence": 0.95,
            "payload": {
                "summary": reason,
                "priority": "high" if ticket.priority_hint == "high" else "normal",
            },
        }

        state.final_decision = fallback
        state.log_event("decision", fallback)

        await self._handle_escalate(state)