from typing import Optional
from models.state import AgentState
from models.reasoning import ReasoningStep
from services.llm_service import LLMReasoner
class RuleBasedReasoner:
    def __init__(self):
        pass
    def next_step(self, state: AgentState) -> Optional[ReasoningStep]:
        t = state.ticket

        # Retry failed actions
        if "get_order" in state.failed_actions:
            return ReasoningStep(
                thought="Retrying order fetch after failure.",
                action="get_order",
                action_input={"order_id": t.order_id},
            )

        # Order fetch
        if t.order_id and "order" not in state.observations:
            return ReasoningStep(
                thought="Fetching order details for grounding.",
                action="get_order",
                action_input={"order_id": t.order_id},
            )

        # Customer context
        if "customer" not in state.observations:
            return ReasoningStep(
                thought="Loading customer profile for risk/context.",
                action="get_customer",
                action_input={"email": t.customer_email},
            )

        # Refund eligibility early check
        if t.order_id and "refund_eligibility" not in state.observations:
            return ReasoningStep(
                thought="Checking refund eligibility before further processing.",
                action="check_refund_eligibility",
                action_input={"order_id": t.order_id, "category": t.category},
            )

        # Early exit optimization
        eligibility = state.observations.get("refund_eligibility", {})
        if eligibility and not eligibility.get("eligible"):
            return None  # No need for further steps

        # Product info
        if t.product_id and "product" not in state.observations:
            return ReasoningStep(
                thought="Fetching product metadata.",
                action="get_product",
                action_input={"product_id": t.product_id},
            )

        # Knowledge base
        if "kb" not in state.observations:
            query = f"{t.category} {t.subject} {t.message}"
            return ReasoningStep(
                thought="Searching knowledge base for policy guidance.",
                action="search_knowledge_base",
                action_input={"query": query},
            )

        return None
class ReasoningEngine:
    def __init__(self, llm_reasoner: Optional[LLMReasoner] = None) -> None:
        self.llm_reasoner = llm_reasoner
        self.rule_reasoner = RuleBasedReasoner()

    def next_step(self, state: AgentState) -> Optional[ReasoningStep]:
        # Try LLM first (if enabled)
        if self.llm_reasoner and self.llm_reasoner.enabled:
            step = self.llm_reasoner.next_step(state)
            if step:
                return step

        # Fallback to rule-based
        return self.rule_reasoner.next_step(state)