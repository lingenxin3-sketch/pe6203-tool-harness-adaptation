# Task 113: under-update from stale required parameters

Status: formal execution evidence reviewed; judge scores complete. This is a real no-update baseline failure, representing the limiting case of missing all persistent knowledge updates. It is not presented as evidence that the selective method missed these parameters.

## Task and changed contract

The user asks for a structured project plan for a log-analysis dashboard, including parsing, error patterns, aggregated statistics and implementation steps. Early `request_planning` requires only `originalRequest` and `tasks`. Middle additionally requires `splitDetails`. Late requires `originalRequest`, `splitDetails`, `tasks`, `priority` and `tags`.

The no-update knowledge in Late still exposes the two Early required parameters. The current environment's contract, recorded alongside the episode, exposes all five. This mismatch directly explains the validation failures below: the server explicitly identifies the missing fields.

## No-update Late trajectory

| Action | Evidence |
|---|---|
| Create a dashboard project | The project state file is created |
| Request planning with `originalRequest` and `tasks` | Server rejects missing `splitDetails`, `priority` and `tags` |
| Retry with `splitDetails` added | Server still rejects missing `priority` and `tags` |
| Repeat essentially the same incomplete call twice | Both calls fail with the same required-field errors |
| Query the next task and later mark a task done | Returned content says `Request not found` because the planning request was never created |
| Final explanation | Blames the task-management system for not functioning; no task-plan file exists |

The actor partly learns from the first error by adding `splitDetails`, but never supplies the remaining Late requirements. This illustrates why reactive retries are not equivalent to refreshing persistent tool knowledge.

There are four MCP-flagged errors and two further returned payloads reporting `status: error` / `Request not found`. The latter have `isError: false`. Therefore the simple `tool_error_count` diagnostic undercounts these semantic failures. The saved raw trajectory, rather than that count alone, supports this analysis. Formal TF/PE scoring still receives the original tool results under the common judge protocol.

## Selective-patch Late comparison

The selective knowledge contains all five required fields. Its first planning call supplies them, including `priority: high` and a list of tags. The run creates the project, registers the plan and retrieves the next task in three tool calls, with no MCP-flagged errors.

The actual `workspace/tasks.json` contains one request with five named tasks, a priority, tags and pending completion/approval states. The tasks cover parsing, categorization, aggregation, interface design, and integration/testing. This verifies **plan creation**, not completion of the dashboard implementation. All five `done` and `approved` fields are false, which must not be described as finished implementation or obtained human approval.

## Interpretation

This example gives direct mechanistic evidence of stale-schema under-update and a successful schema repair. It does not isolate the benefit of dependency expansion: copying the changed planning schema may already be sufficient. The predeclared closure-disabled comparison on this task is required before attributing an effect to that component. It also does not establish whole-benchmark superiority; the complete score tables and other failures remain necessary.

## Evidence paths

- No-update Late: `runs/final-v1/repeat-0/no_update/iter5/113/result.json`.
- Selective Late: `runs/final-v1/repeat-0/selective_patch/iter5/113/result.json`.
- Saved plan: `runs/final-v1/repeat-0/selective_patch/iter5/113/workspace/tasks.json`.
- Early/Middle/Late contracts: `artifacts/inventory/original.json`, `iter3.json`, `iter5.json`; scoped versions also appear in the episode records.

## Formal judge disagreement

The fixed local judge assigned no-update Late **TF 10, grounding 10 and PE 10**. Its reasoning says all seven requirements were met while also acknowledging that tasks could not be registered or accessed. The actual saved `.agentic-tools-mcp/tasks/tasks.json` is project state; it is not the missing `workspace/tasks.json` planning request. Four planning calls failed required-field validation, and no registered request was available to subsequent calls.

This disagreement limits the score's ability to measure the demonstrated schema failure. The selective trajectory's successful registration remains an execution fact, but it must not be described as a TF recovery from this already-maximal no-update score. The benchmark score stays unchanged. `analysis/artifact-review.json` supplies the narrow persistence checks; it is supplementary evidence, not a replacement metric or an estimate for all benchmark tasks.
