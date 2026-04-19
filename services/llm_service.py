import json
import os
import re
from typing import Any, Optional

from models.reasoning import ReasoningStep
from models.state import AgentState

class LLMReasoner:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self._model = None
        if self.api_key:
            try:
                import google.generativeai as genai  # type: ignore

                genai.configure(api_key=self.api_key)
                self._model = genai.GenerativeModel(self.model_name)
            except Exception:  # noqa: BLE001
                # Fail open and continue with rule-based reasoning.
                self._model = None

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self._model)

    def next_step(self, state: AgentState) -> Optional[ReasoningStep]:
        if not self.enabled or self._model is None:
            return None
        prompt = self._build_prompt(state)
        try:
            response = self._model.generate_content(prompt)
            text = getattr(response, "text", "") or ""
            return self._parse_react_output(text)
        except Exception:  # noqa: BLE001
            # Always fail open to the rule-based reasoner.
            return None

    def _build_prompt(self, state: AgentState) -> str:
        ticket = state.ticket
        observation_json = json.dumps(state.observations, ensure_ascii=True)
        return (
            "You are a support resolution reasoning module. "
            "Return exactly this format and nothing else:\n"
            "Thought: <one sentence>\n"
            "Action: <tool_name>\n"
            "Action Input: <valid JSON object>\n\n"
            "Allowed tools:\n"
            "- get_order {\"order_id\": \"...\"}\n"
            "- get_customer {\"email\": \"...\"}\n"
            "- get_product {\"product_id\": \"...\"}\n"
            "- search_knowledge_base {\"query\": \"...\"}\n"
            "- check_refund_eligibility {\"order_id\": \"...\"}\n\n"
            "Do NOT choose action tools (issue_refund/send_reply/escalate).\n\n"
            f"Ticket: id={ticket.ticket_id}, category={ticket.category}, order_id={ticket.order_id}, "
            f"email={ticket.customer_email}, subject={ticket.subject}, message={ticket.message}, "
            f"product_id={ticket.product_id}\n"
            f"Current observations: {observation_json}\n"
            f"Current step_count: {state.step_count}\n"
        )

    def _parse_react_output(self, output: str) -> Optional[ReasoningStep]:
        thought_match = re.search(r"Thought:\\s*(.+)", output)
        action_match = re.search(r"Action:\\s*([a-zA-Z_]+)", output)
        action_input_match = re.search(r"Action Input:\\s*(\\{.*\\})", output, re.DOTALL)
        if not thought_match or not action_match or not action_input_match:
            return None

        action = action_match.group(1).strip()
        if action not in {
            "get_order",
            "get_customer",
            "get_product",
            "search_knowledge_base",
            "check_refund_eligibility",
        }:
            return None

        try:
            action_input: Any = json.loads(action_input_match.group(1).strip())
        except json.JSONDecodeError:
            return None
        if not isinstance(action_input, dict):
            return None

        return ReasoningStep(
            thought=thought_match.group(1).strip(),
            action=action,
            action_input=action_input,
        )
