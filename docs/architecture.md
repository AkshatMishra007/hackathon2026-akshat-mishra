# Architecture Diagram (Text)

```
Ticket Queue -> Worker Pool (asyncio, max 3-5)
                  |
                  v
          Agent Orchestrator
          (Thought -> Action -> Observation loop)
             |      |        |
             |      |        +--> Audit logger (per-step)
             |      +--> Tool Layer (read/write tools, retries, timeouts)
             +--> Decision Engine (refund/reply/escalate + confidence)
                  |
                  v
            Final Action Execution
                  |
                  v
          logs/<ticket_id>.json + audit_log.json
```
