# Verified result tables

Source: `final-v1`; split: **test**; 18 tasks; 1 repetition per configuration.

Local rubric scores. TF and PE range from 1 to 10; higher is better. ECS is the original cross-version formula. Single-run differences are descriptive and do not establish statistical significance.

## Main results

| Policy | Early TF / PE | Middle TF / PE | Late TF / PE | ECS |
| --- | --- | --- | --- | --- |
| No update | 6.83 / 6.56 | 7.28 / 7.33 | 7.44 / 7.89 | 6.28 |
| Full rewrite | 6.28 / 7.50 | 7.06 / 7.83 | 6.72 / 7.17 | 5.24 |
| Selective patch | 7.11 / 7.33 | 7.61 / 7.61 | 7.17 / 7.39 | 6.33 |

Each stage mean uses 18 episodes per policy. ECS aligns the same tasks across all three versions.

All policies use identical initial knowledge at Early, with no adaptation. Any Early score gap is execution or judging variation, not an update benefit. One repetition cannot separate every source of variation from later policy differences.

## Middle recovery and retention

| Cohort | Policy | n | TF | Delta vs Early | Delta vs no update |
| --- | --- | --- | --- | --- | --- |
| changed | No update | 9 | 6.89 | +0.00 | +0.00 |
| unaffected | No update | 9 | 7.67 | +0.89 | +0.00 |
| changed | Full rewrite | 9 | 8.44 | +1.67 | +1.56 |
| unaffected | Full rewrite | 9 | 5.67 | -0.11 | -2.00 |
| changed | Selective patch | 9 | 7.89 | +1.22 | +1.00 |
| unaffected | Selective patch | 9 | 7.33 | -0.22 | -0.33 |

Changed = scoped contracts differ from Early. Recovery compares changed tasks with same-version no-update. Retention compares unaffected tasks with the same policy at Early. Negative differences are losses; cohorts and denominators are stage-specific.

## Late recovery and retention

| Cohort | Policy | n | TF | Delta vs Early | Delta vs no update |
| --- | --- | --- | --- | --- | --- |
| changed | No update | 10 | 7.50 | +0.30 | +0.00 |
| unaffected | No update | 8 | 7.38 | +1.00 | +0.00 |
| changed | Full rewrite | 10 | 7.70 | +0.60 | +0.20 |
| unaffected | Full rewrite | 8 | 5.50 | +0.25 | -1.88 |
| changed | Selective patch | 10 | 7.30 | +0.70 | -0.20 |
| unaffected | Selective patch | 8 | 7.00 | -0.75 | -0.38 |

Changed = scoped contracts differ from Early. Recovery compares changed tasks with same-version no-update. Retention compares unaffected tasks with the same policy at Early. Negative differences are losses; cohorts and denominators are stage-specific.

## Results by change category

| Version | Change | Policy | n | TF / PE | Delta vs no update |
| --- | --- | --- | --- | --- | --- |
| Middle | Tool | No update | 3 | 8.00 / 9.00 | +0.00 |
| Middle | Tool | Full rewrite | 3 | 9.33 / 9.33 | +1.33 |
| Middle | Tool | Selective patch | 3 | 10.00 / 10.00 | +2.00 |
| Middle | Parameter | No update | 8 | 7.00 / 7.75 | +0.00 |
| Middle | Parameter | Full rewrite | 8 | 8.50 / 9.12 | +1.50 |
| Middle | Parameter | Selective patch | 8 | 7.62 / 8.12 | +0.62 |
| Middle | Description | No update | 9 | 6.89 / 7.67 | +0.00 |
| Middle | Description | Full rewrite | 9 | 8.44 / 9.00 | +1.56 |
| Middle | Description | Selective patch | 9 | 7.89 / 8.33 | +1.00 |
| Late | Tool | No update | 7 | 7.71 / 8.86 | +0.00 |
| Late | Tool | Full rewrite | 7 | 8.43 / 9.00 | +0.71 |
| Late | Tool | Selective patch | 7 | 8.71 / 9.00 | +1.00 |
| Late | Parameter | No update | 10 | 7.50 / 8.60 | +0.00 |
| Late | Parameter | Full rewrite | 10 | 7.70 / 7.90 | +0.20 |
| Late | Parameter | Selective patch | 10 | 7.30 / 7.60 | -0.20 |
| Late | Description | No update | 9 | 7.22 / 8.44 | +0.00 |
| Late | Description | Full rewrite | 9 | 7.78 / 8.33 | +0.56 |
| Late | Description | Selective patch | 9 | 7.33 / 7.78 | +0.11 |

Compared with Early using captured authoritative evaluation tools: Tool = added/removed names; Parameter = changed schema on surviving names; Description = changed description on surviving names. Categories overlap; cohort difficulty is descriptive and cannot isolate a mutation effect.

A lower score identifies a harder observed cohort, not the causal effect of that change type. Empty categories have no score. Category counts must not be summed as unique episodes.

## Adaptation cost

| Policy | Calls | Total tokens | Request seconds | Token saving vs full |
| --- | --- | --- | --- | --- |
| No update | 0 | 0 | 0.00 | 100.0% |
| Full rewrite | 36 | 104,472 | 359.32 | 0.0% |
| Selective patch | 19 | 36,449 | 123.08 | 65.1% |

Totals include both environment transitions and rejected update calls. No-update has no adaptation generation, but that alone says nothing about task quality. Token savings are relative to full rewrite, not an overall utility score.

## Execution and judging cost

| Policy | Component | Calls | Total tokens | Request seconds |
| --- | --- | --- | --- | --- |
| No update | agent | 426 | 3,007,538 | 27204.20 |
| No update | judge | 54 | 406,669 | 1673.41 |
| Full rewrite | agent | 403 | 2,682,307 | 11202.20 |
| Full rewrite | judge | 54 | 397,788 | 3141.77 |
| Selective patch | agent | 405 | 2,985,921 | 5773.46 |
| Selective patch | judge | 54 | 408,974 | 4177.25 |

All recorded API charges are USD 0 because inference is local. Hardware and electricity are not monetized. Request time is not whole-experiment duration; cache reuse, hardware and execution order affect timing.

## Dependency-expansion component comparison

| Task | Version | TF on / off | Delta TF | PE on / off | Notes on / off |
| --- | --- | --- | --- | --- | --- |
| 113 | Middle | 4.00 / 10.00 | -6.00 | 10.00 / 10.00 | 6 / 2 |
| 416 | Middle | 10.00 / 10.00 | +0.00 | 10.00 / 10.00 | 4 / 1 |
| 113 | Late | 10.00 / 10.00 | +0.00 | 10.00 / 10.00 | 9 / 5 |
| 416 | Late | 4.00 / 10.00 | -6.00 | 5.00 / 10.00 | 4 / 1 |
| 113 | Early | 4.00 / 10.00 | -6.00 | 10.00 / 10.00 | 0 / 0 |
| 416 | Early | 10.00 / 10.00 | +0.00 | 10.00 / 10.00 | 0 / 0 |

On = the main selective method; off = the predeclared selective variant without reference expansion. Early performs no updates. The six pairs are supplementary, with two predeclared tasks and one repetition; they are not a second full benchmark.

## Fixed-budget execution diagnostics

| Policy | Step-limit episodes | Length-limited replies | Calls with pruning | Rejected updates |
| --- | --- | --- | --- | --- |
| No update | 7 | 2 | 11 | 0 |
| Full rewrite | 6 | 1 | 6 | 0 |
| Selective patch | 4 | 1 | 16 | 0 |

Episode counts and model-response counts have different denominators. An output reaching its length limit does not always abort an episode. Context pruning keeps original instructions and the task; full raw histories remain saved. These common resource limits can mediate observed policy differences.

## Recorded execution exceptions

4 terminal execution exception(s) remain included in the scored grid.

| Task | Policy | Version | TF | PE |
| --- | --- | --- | --- | --- |
| 117 | Full rewrite | Late | 9.00 | 10.00 |
| 273 | No update | Late | 7.00 | 4.00 |
| 278 | Selective patch | Late | 4.00 | 2.00 |
| 393 | Selective patch | Early | 7.00 | 5.00 |

Original failure receipts and incremental traces are preserved. Scoring a failed trace is not a retry or a claim that task execution completed successfully.
