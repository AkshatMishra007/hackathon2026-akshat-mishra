from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from execution.worker import run_support_workers
from web.database import init_db, list_runs, save_run


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Autonomous Support Agent Web API", version="1.0.0", lifespan=lifespan)
WEB_DIR = Path(__file__).resolve().parent


class RunRequest(BaseModel):
    max_workers: int = Field(default=3, ge=1, le=5)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "static" / "index.html")


@app.post("/api/run")
async def run_agent(payload: RunRequest) -> dict[str, Any]:
    settings = get_settings()
    override = type(settings)(
        **{
            **asdict(settings),
            "max_workers": payload.max_workers,
        }
    )
    results = await run_support_workers(override)
    summary = {
        "refund": sum(1 for r in results if (r.final_decision or {}).get("decision") == "refund"),
        "reply": sum(1 for r in results if (r.final_decision or {}).get("decision") == "reply"),
        "escalate": sum(1 for r in results if (r.final_decision or {}).get("decision") == "escalate"),
        "dead_letter": sum(1 for r in results if r.dead_letter),
    }
    run_id = save_run(len(results), payload.max_workers, summary)
    return {"run_id": run_id, "tickets_processed": len(results), "summary": summary}


@app.get("/api/runs")
def get_runs() -> dict[str, Any]:
    try:
        return {"runs": list_runs()}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
