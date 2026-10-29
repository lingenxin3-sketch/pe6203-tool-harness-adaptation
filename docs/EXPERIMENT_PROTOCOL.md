# Original-round experiment protocol (historical)

> Scope: this document records the protocol declared for final-v1, including its original one-run compute budget and pre-scoring amendment. Two added rounds were later completed without rewriting that original plan. Only final-v1 and final-r3 form the 324-observation descriptive comparison; R2 remains separate due to actual input differences. See the [final results](https://github.com/lingenxin3-sketch/pe6203-tool-harness-adaptation/blob/experiments/repeats-20261029/docs/追加实验/交付与核验.md). Historical implementation-stage notes are not current course submission instructions.

## Research question

Can dependency-aware selective updates to tool knowledge recover performance after persistent MCP tool changes while retaining unaffected capabilities and reducing adaptation work relative to a full rewrite?

## Fixed resources

The benchmark source is MCPEvol-Bench commit `888c779a0fe735f612ca62bdd1fdd7c9e6bf8701`. Original, iter3 and iter5 service archives are downloaded from the repository-linked dataset. Archive and local-model SHA-256 values are stored next to the downloads. Service code is not edited. Windows module URL compatibility is applied uniformly at process startup.

The base model is Qwen3-4B-Instruct-2507 Q4_K_M, served by llama.cpp b11900 on an RTX 3060 Laptop GPU with 6 GB VRAM. All three policies use identical inference parameters and a fixed maximum of 12 agent rounds. A single runtime verification opportunity is available to every strategy and consumes a normal round. It supplies actual file changes, not task labels or expected answers.

## Task selection before policy evaluation

The final subset has 18 distinct task IDs drawn from the official `chosen_idx.json`. IDs are frozen in `configs/experiment.json` before evaluating any policy on these tasks. Selection is based on local service availability, not observed scores. Development IDs 3 and 101 are disjoint from the final set.

The subset covers local file, task, project and memory workflows. It deliberately excludes workflows needing paid accounts. This limits external validity and must be stated beside reported results. `artifacts/coverage.json` records which contracts changed, independently of task outcomes.

The official task questions are unchanged. Resource fixtures are copied into a fresh per-episode workspace, with a matching `anotation_path` copy for questions that explicitly name that prefix. Each episode receives a resource file listing, as the official agent does. State must not carry over between policies or task executions. Only the policy's tool knowledge carries from Early to Middle to Late within one task/strategy sequence.

## Three required policies

1. **No update:** preserve Early schemas and usage notes across both subsequent environment changes.
2. **Full rewrite:** replace schemas from the current authoritative interface and regenerate every scoped usage note.
3. **Selective patch:** detect added, removed and modified contracts; expand the impact set transitively through tool-name references; replace current schemas and regenerate only impacted notes. Preserve other notes exactly.

Both updating policies use the same updater model, prompt and output validation. The updater sees current tool contracts only. It never sees a task question, reference tool calls, mutation task annotations, execution scores or held-out answers. JSON that misses requested tool names or invents extra names is rejected; prior knowledge is retained and the rejection is logged.

Tool scope follows the official task's server/tool metadata at Early; later it includes surviving original tool names and newly added tools from those servers. All policies use the same scope construction. Real execution always targets the current official server version.

## Evaluation and cost

Use the official TF and PE judge rubric, original score aggregation and original population-standard-deviation ECS implementation. The upstream evaluation script's missing import and eager hard-coded MCP connection are bypassed by extracting its pure functions unchanged, while supplying captured current tool contracts. This portability adapter is disclosed and test-checked.

For each strategy, report Early/Middle/Late TF and PE, overall ECS, changed-task recovery and unchanged-task retention. API charges are zero for local inference; report actual tokens and wall time separately for updating, execution and judging. Electricity and hardware depreciation are not priced.

Only one run per configuration is planned under limited local compute, as allowed by the assignment. This does not quantify stochastic repeat variability. Local judge scores are not instructor-certified scores. Development testing found that the 4B judge accepted unsupported completion claims. Before the formal run, the judge was fixed to local Qwen2.5-7B-Instruct Q4_K_M, with the unchanged official rubric. Two saved development trajectories were used for calibration: a missing-file case received TF 6 and an actual-file case received TF 10. These two examples do not establish judge reliability; grounding judgments were still too generous. Compare judge reasoning with saved calls and actual generated files, and report disagreements rather than silently changing the rubric-based scores. Calibration responses are in `artifacts/judge-calibration/`.

Execution and judging run in separate phases to fit the 6 GB GPU. All actor/updater work uses the same 4B model; only after execution finishes is that server stopped and the 7B judge started. Judging uses the stored trajectories and frozen evaluation tools. The complete actor record is retained separately before scores are added.

## Completeness and failure rules

The primary grid has 18 tasks × 3 strategies × 3 environment versions = 162 episodes. An aggregator must refuse a final summary if any planned row is missing, duplicated, invalid or unscored. Infrastructure failures remain explicit records and cannot be removed to improve the mean.

Evidence-handling clarification added after an observed execution exception, before formal scoring: if an episode terminates after recording model responses and tool events, its partial trajectory is assembled from those records and scored as the failed execution, without retrying it. The original `failure-record.json` and event hashes are preserved. `execution_status: infrastructure_error` remains explicit even when its scoring status becomes `awaiting_judge` or `evaluated`. Unknown whole-episode wall time is null; recorded request timings remain usable. Empty or inconsistent traces are refused. This bookkeeping repair does not change model settings, tools, agent actions, adaptation methods or benchmark labels, and applies equally to all policies.

Under-update: changed knowledge or a necessary related rule was not updated, causing a stale/invalid operation or an unmet requirement. Over-update: a formerly correct, unrelated rule was changed and contributed to a regression. Distinguish these from model-level planning errors, missing benchmark resources, service execution errors and judge errors. Claims of causality require a concrete trajectory or a controlled component comparison.

## Planned component comparison

Compare selective patch with dependency expansion disabled on predeclared dependency-bearing tasks 113 and 416, across all three versions. The component changes only the impact-set expansion, not the model or scoring protocol. This focused ablation is supplementary and is not substituted for the 18-task main grid. Interpretation must include cases where expansion does not help.

## Deliverables

Code, installation and execution commands, frozen configuration, raw run evidence, required metrics and cost tables, failure examples, limitations and a final report. Slides were outside the original implementation-stage deliverables; the course presentation requirements are listed in `docs/REQUIREMENTS_EVIDENCE_ZH.md`. Human team contributions should be recorded only after those members perform the work; AI assistance must be disclosed.

## Pre-scoring judge capacity amendment

Before the first formal score, all 162 main prompts were checked with the downloaded judge vocabulary. Four exceeded the original 16,384 response-reserved budget; the maximum estimate was 20,317. Formal judge server capacity is uniformly 24,576, with the same model, rubric, complete official prompt, decoding and response limit. Actor/updater capacity and frozen core source remain unchanged. See `configs/judge-capacity.json` and `artifacts/judge-capacity-amendment.json`. This infrastructure amendment must be disclosed in the report; it is not a per-policy setting or a rerun selected by scores.
