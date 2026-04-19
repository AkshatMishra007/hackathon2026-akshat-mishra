import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    ticket_file: str = "data/tickets.json"
    db_file: str = "data/mock_db.json"
    logs_dir: str = "logs"
    audit_rollup_file: str = "audit_log.json"
    max_workers: int = 3
    max_reasoning_steps: int = 6
    max_tool_retries: int = 2
    min_tool_delay_seconds: float = 0.05
    max_tool_delay_seconds: float = 0.25
    tool_failure_rate: float = 0.15
    malformed_data_rate: float = 0.08
    tool_timeout_seconds: float = 1.0
    openai_api_key: str | None = None
    gemini_api_key: str | None = None


def get_settings() -> Settings:
    workers = int(os.getenv("MAX_WORKERS", "3"))
    workers = max(1, min(workers, 5))
    return Settings(
        ticket_file=os.getenv("TICKET_FILE", "data/tickets.json"),
        db_file=os.getenv("DB_FILE", "data/mock_db.json"),
        logs_dir=os.getenv("LOGS_DIR", "logs"),
        audit_rollup_file=os.getenv("AUDIT_ROLLUP_FILE", "audit_log.json"),
        max_workers=workers,
        max_reasoning_steps=int(os.getenv("MAX_REASONING_STEPS", "6")),
        max_tool_retries=int(os.getenv("MAX_TOOL_RETRIES", "2")),
        min_tool_delay_seconds=float(os.getenv("MIN_TOOL_DELAY_SECONDS", "0.05")),
        max_tool_delay_seconds=float(os.getenv("MAX_TOOL_DELAY_SECONDS", "0.25")),
        tool_failure_rate=float(os.getenv("TOOL_FAILURE_RATE", "0.15")),
        malformed_data_rate=float(os.getenv("MALFORMED_DATA_RATE", "0.08")),
        tool_timeout_seconds=float(os.getenv("TOOL_TIMEOUT_SECONDS", "1.0")),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
    )
