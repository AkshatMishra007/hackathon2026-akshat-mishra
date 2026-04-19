# Autonomous Support Resolution Agent

## Overview

An agentic system that autonomously processes customer support tickets using a multi-step reasoning loop, tool execution, and decision engine.

---

## Features

* Multi-step reasoning (Thought → Action → Observation loop)
* Tool chaining (≥ 3 tools per ticket)
* Retry + timeout handling
* Concurrent ticket processing using asyncio
* Full audit logging
* Safe execution with escalation fallback

---

## Architecture

The system consists of:

1. Ticket Intake
2. Agent Orchestrator
3. Tool Layer
4. Reliability Layer
5. Execution + Audit

---

## Tech Stack

* Python (asyncio)
* FastAPI (optional services)
* Gemini / OpenAI (optional LLM)
* JSON-based mock DB

---

## Project Structure

```
.
├── agent/
├── tools/
├── services/
├── models/
├── execution/
├── data/
├── logs/
├── main.py
├── requirements.txt
├── README.md
```

---

## Setup Instructions

```bash
git clone https://github.com/AkshatMishra007/hackathon2026-akshat-mishra.git
cd hackathon2026-akshat-mishra

python -m venv venv
venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

---

## Run the Project

```bash
python main.py
```

---

## Input

* `data/tickets.json` → 20 support tickets

---

## Output

* `logs/<ticket_id>.json` → per-ticket logs
* `audit_log.json` → full system trace

---
## Demo Video

## Agent Flow

1. Reasoning engine selects next tool
2. Orchestrator executes with retry + validation
3. Observations are stored in state
4. Decision engine determines:

   * refund
   * reply
   * escalate
5. Action is executed safely

---

## Failure Handling

* Tool retries with backoff
* Malformed data detection
* Circuit breaker after repeated failures
* Dead-letter queue for critical errors

---

## Concurrency

* Worker pool processes multiple tickets concurrently using asyncio
* Configurable via environment variables

---

## Environment Variables (Optional)

Create a `.env` file if using API-based reasoning:

```
OPENAI_API_KEY=your_key
GEMINI_API_KEY=your_key
```

---

## 🎬 Demo Video
https://drive.google.com/file/d/1LdRQ85e2N89TzB8UEAIVLgneKlny-dSV/view?usp=drive_link

Run the project and observe:

* Ticket processing in terminal
* Logs generated in `/logs`
* Full execution trace in `audit_log.json`

---

## Hackathon Requirements Covered

* ≥ 3 tool calls per ticket
* Full audit trail
* Autonomous decision making
* Robust failure handling
