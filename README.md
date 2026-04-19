# Autonomous Support Resolution Agent

## Overview

This project implements an agentic system that automatically processes customer support tickets.  
Instead of a fixed pipeline, the system follows a **multi-step reasoning loop**, where it decides what to do next based on the current state.

The goal was to simulate how a real support system works — combining reasoning, tool usage, and safe decision-making.

---

## Key Features

- Multi-step reasoning (Thought → Action → Observation)
- Tool chaining (multiple tools used per ticket)
- Concurrent processing using asyncio workers
- Retry handling and failure management
- Full audit logging for transparency
- Safe execution with escalation fallback

---

## How the System Works

1. Tickets are loaded from `data/tickets.json`
2. Each ticket is processed by a worker
3. The agent:
   - Thinks (decides next step)
   - Calls tools (order, customer, refund, etc.)
   - Stores observations
4. A decision is made:
   - refund
   - reply
   - escalate
5. Action is executed safely
6. All steps are logged

---

## Project Structure


.
├── agent/ # reasoning, orchestrator, decision logic
├── tools/ # all tool implementations
├── services/ # retry, logging, LLM services
├── models/ # data models
├── execution/ # worker system
├── data/ # input tickets
├── logs/ # generated logs
├── app/
│ └── main.py # entry point
├── requirements.txt


---

## Setup

```bash
git clone https://github.com/AkshatMishra007/hackathon2026-akshat-mishra.git
cd hackathon2026-akshat-mishra

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
```

## Run the Project 
 
```bash
python -m app.main

```

## Input  

data/tickets.json → contains 20 tickets

##  Output
logs/<ticket_id>.json → individual ticket logs
audit_log.json → complete execution trace

## Demo Video

https://drive.google.com/file/d/1LdRQ85e2N89TzB8UEAIVLgneKlny-dSV/view?usp=drive_link

## Failure Handling

The system handles multiple failure scenarios:

Retry logic for tool failures
Handling malformed tool responses
Circuit breaker after repeated errors
Dead-letter logging for critical failures
Re-check before irreversible actions (like refund)

## Concurrency

Multiple workers process tickets in parallel
Implemented using asyncio queue
Improves performance and realism

## Environment Variables (Optional)

If using API-based reasoning:
OPENAI_API_KEY=your_key

GEMINI_API_KEY=your_key

## What I Learned

This project helped me understand how real systems are not just about solving a problem once, but handling edge cases, failures, and making safe decisions step by step.

## Hackathon Requirements Covered

≥ 3 tool calls per ticket
Autonomous decision making
Full audit logging
Failure handling
Concurrent processing


