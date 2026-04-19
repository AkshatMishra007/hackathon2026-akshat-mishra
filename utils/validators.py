from typing import Any, Mapping


class ValidationError(ValueError):
    """Raised when a tool output or decision payload is invalid."""


def require_keys(payload: Mapping[str, Any], keys: list[str], context: str) -> None:
    missing = [k for k in keys if k not in payload]
    if missing:
        raise ValidationError(f"{context} missing keys: {missing}")


def validate_tool_observation(action: str, observation: Mapping[str, Any]) -> None:
    if action == "get_order":
        require_keys(observation, ["found"], "get_order")
    elif action == "get_customer":
        require_keys(observation, ["found"], "get_customer")
    elif action == "check_refund_eligibility":
        require_keys(observation, ["eligible", "reason"], "check_refund_eligibility")
    elif action == "search_knowledge_base":
        require_keys(observation, ["query", "hits"], "search_knowledge_base")
    elif action == "get_product":
        require_keys(observation, ["found"], "get_product")


def validate_decision_payload(decision_type: str, payload: Mapping[str, Any]) -> None:
    if decision_type == "refund":
        require_keys(payload, ["order_id", "amount", "reason"], "refund decision payload")
    elif decision_type == "escalate":
        require_keys(payload, ["summary", "priority"], "escalate decision payload")
    elif decision_type == "reply":
        require_keys(payload, ["message"], "reply decision payload")
