# Failure Mode Analysis

## 1) Tool transient failure / timeout
- **Scenario**: `get_order` or `send_reply` fails due to simulated transient issue.
- **Handling**: `RetryService` retries with backoff up to configured budget.
- **Outcome**: On repeated failure, error is logged in audit trail; decision can still proceed with partial context.

## 2) Malformed tool payload
- **Scenario**: tool returns malformed data (simulated via `MalformedToolDataError`).
- **Handling**: orchestrator catches malformed errors, marks `"malformed_data"` in state errors.
- **Outcome**: decision engine raises escalation likelihood to avoid unsafe action.

## 3) Final action execution failure
- **Scenario**: irreversible action or comms action repeatedly fails.
- **Handling**: orchestrator catches exception in execution stage and routes ticket to dead-letter path.
- **Outcome**: `dead_letter = true` with full context in per-ticket log and rollup audit.

## 4) Eligibility drift before irreversible refund
- **Scenario**: decision selected `refund`, but eligibility becomes invalid by action time (state drift/recheck mismatch).
- **Handling**: orchestrator re-checks refund eligibility immediately before `issue_refund`.
- **Outcome**: refund is blocked safely and ticket is auto-escalated with structured context.

## 5) Duplicate refund attempt
- **Scenario**: repeated `issue_refund` call for an already-refunded order.
- **Handling**: refund tool enforces idempotency and returns `{"ok": false, "reason": "already_refunded"}`.
- **Outcome**: prevents duplicate irreversible payouts and leaves explicit evidence in tool/audit logs.
