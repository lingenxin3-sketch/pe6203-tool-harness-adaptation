# Task 28: an observed over-update regression candidate

Status: execution evidence reviewed; formal judge scores complete. This is a real formal-run example, not a synthetic demonstration. It supports an association between unnecessary rewriting and lost task-creation behavior; it does not establish a note-level causal effect from repeated controlled interventions.

## Request and unchanged tools

The task asks the agent to compare yesterday's and today's logs, summarize changes, and save to-do tasks for unresolved issues in `tasks.md` under the project directory. In Middle, the scoped contracts for `tasks_add`, `tasks_setup` and `read_multiple_files` are unchanged from Early. The full-rewrite audit reports empty added/removed/modified/impacted sets, but regenerates all three usage notes anyway.

## What changed in the knowledge

Early `tasks_setup` guidance explicitly states that it creates the file if it does not exist. The rewritten note says to initialize a source from a path, provide `source_path` and `workspace`, and use the returned ID in `tasks_add`; the explicit file-creation statement is omitted. This omission is a plausible contributing mechanism, not proven to be the sole cause. The rewritten note still says to call setup once, yet the actor fails to follow it.

## Observed trajectory

| Step | Full rewrite, Middle | Observed consequence |
|---|---|---|
| 1 | Read `txt/log_yesterday.txt` and `txt/log_today.txt` | Both logs are returned |
| 2 | Call `tasks_add` with invented `source_id_1` before setup | Source not found; server requests setup |
| 3 | Initialize the yesterday `.txt` log as the task source | Server rejects `.txt`; supported types include `.md` |
| 4 | Initialize the today `.txt` log as the task source | Same rejection |
| Final | Assert that the available tools cannot create the requested task file | No file is created; the claim misdiagnoses the tool capability |

By contrast, full-rewrite Early, no-update Early/Middle and selective-patch Middle initialize `anotation_path/markdown/tasks.md`, use the returned source ID, and add tasks. The saved files confirm task creation. The within-policy Early-to-Middle comparison demonstrates loss of a previously observed operation even though the scoped Middle contracts are unchanged; the same-version comparisons provide additional context.

It does **not** show perfect success in the retained runs: the task content asserts that yesterday's database failure is still unresolved even though today's supplied log does not show it, and adds a speculative startup check. File creation and factual correctness must therefore be assessed separately. An ideal answer would identify the persistent disk-space warning and qualify the database issue rather than inventing persistence.

Selective-patch Late also fails to create the file despite preserving the two task-management notes. A changed file-reading contract/description and a different prompt context can alter later planning. This is evidence against claiming that preserving individual notes guarantees retention, and it prevents attributing every failure to the rewritten setup note alone.

## Evidence paths

- Full-rewrite failure and update diff: `runs/final-v1/repeat-0/full_rewrite/iter3/28/result.json`.
- Within-policy Early file-creation evidence: `runs/final-v1/repeat-0/full_rewrite/original/28/result.json` and its `workspace/anotation_path/markdown/tasks.md`.
- Early comparison: `runs/final-v1/repeat-0/no_update/original/28/result.json` and its `workspace/anotation_path/markdown/tasks.md`.
- Selective Middle comparison: `runs/final-v1/repeat-0/selective_patch/iter3/28/result.json` and its saved task file.
- Selective Late counterexample: `runs/final-v1/repeat-0/selective_patch/iter5/28/result.json`.

Do not label all missing files as over-update. This case specifically combines unchanged contracts, unnecessary rewriting and an observed regression; stronger causal attribution requires a controlled same-context note intervention.
