# Reproducing the original pipeline and inspecting completed repeats

The installation and full-pipeline commands below reproduce the original final-v1 experiment (162 main episodes plus 6 component-comparison episodes). They do not reproduce all three completed rounds by themselves. The completed project has 486 scored records; only final-v1 and final-r3 form the 324-observation descriptive comparison. See the [final results](https://github.com/lingenxin3-sketch/pe6203-tool-harness-adaptation/blob/experiments/repeats-20261029/docs/追加实验/交付与核验.md) for round-specific data, exclusions and evidence downloads. Existing scored directories and published ZIPs must be preserved.

## Tested environment and downloads

Windows, Python 3.14.2, Node.js 24.16, PowerShell 7, Git, curl, and an NVIDIA RTX 3060 Laptop GPU (6 GB VRAM). The inference backend is llama.cpp b11900 CUDA 12.4. Model and server downloads total approximately 11 GB, with additional space needed for extraction and per-episode resources. Reserve at least 30 GB and allow several hours for execution. No paid API, API key or account is used. Internet access is needed for public downloads, not for local inference.

Run commands from the project root. The installation below uses a project-local environment; it does not change global Python packages. Use `pwsh` (PowerShell 7) for model scripts.

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-lock.txt
.venv/Scripts/python.exe -m pip install --no-deps -e .
git clone https://github.com/Octobrist/MCPEvol-Bench upstream
git -C upstream checkout 888c779a0fe735f612ca62bdd1fdd7c9e6bf8701
.venv/Scripts/python.exe scripts/download_runtime.py
.venv/Scripts/python.exe scripts/download_runtime.py --judge-only
.venv/Scripts/python.exe scripts/verify_downloads.py
Expand-Archive -LiteralPath runtime/downloads/llama.zip -DestinationPath runtime/llama -Force
Expand-Archive -LiteralPath runtime/downloads/cudart.zip -DestinationPath runtime/llama -Force
.venv/Scripts/python.exe scripts/prepare_servers.py
.venv/Scripts/python.exe scripts/audit_server_sources.py
.venv/Scripts/python.exe scripts/probe_servers.py
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

Clone only if `upstream` does not already exist. The download script resumes `.part` files and skips existing complete filenames. Hugging Face downloads use exact repository revisions from `artifacts/dependency-revisions.json`; their linked content hashes were checked against the frozen downloads. The original download URLs remain recorded for provenance. The separate verification step MUST pass before extraction or execution: frozen SHA-256 values, not filenames alone, define the actual dependencies. If a hash differs, investigate and obtain the recorded version; do not silently replace the lock file.

## Small development run

This runs development task 3 under all three strategies and environment versions (9 episodes). It is separate from the formal test set. Give the output a new name each time; the runner refuses to overwrite an existing directory.

```powershell
pwsh -NoProfile -File scripts/start-local-model.ps1
.venv/Scripts/python.exe -m tool_adapt run --split development --task-limit 1 --output runs/my-development-run
pwsh -NoProfile -File scripts/stop-local-model.ps1 -Role actor
pwsh -NoProfile -File scripts/start-judge.ps1
.venv/Scripts/python.exe scripts/judge_with_capacity.py runs/my-development-run
.venv/Scripts/python.exe -m tool_adapt analyze runs/my-development-run
```

Wait until the model reports it is listening before the next command. A startup script prints the process ID before model loading finishes. The automated full pipeline waits for readiness itself. Stop the judge before returning to actor work on a 6 GB GPU:

```powershell
pwsh -NoProfile -File scripts/stop-local-model.ps1 -Role judge
```

## Frozen full experiment

On a fresh reproduction checkout where neither formal output directory exists:

```powershell
.venv/Scripts/python.exe scripts/run_full_pipeline.py
```

The pipeline executes 162 main episodes and 6 component-comparison episodes, switches from the 4B actor to the 7B judge, scores the stored traces, and checks completeness before aggregating. Output folders are `runs/final-v1` and `runs/ablation-v1`. Phase and process ID are in `runtime/pipeline-state.json`; phase logs are in `runtime/`. Re-running this command against an existing formal directory intentionally fails. Preserve interrupted runs and diagnose them; do not delete or cherry-pick failed episodes to improve reported performance.

The model, task IDs, decoding settings, scope, agent loop and update methods must remain fixed during formal execution. Documentation and read-only audit scripts can be improved without changing this protocol.

If an episode terminates with a recorded partial trace, the pipeline's post-execution step preserves its original `failure-record.json` and assembles the existing events for judging. This is failure accounting, not a retry. `execution_status` remains `infrastructure_error` and the failed attempt stays in the denominator. No completion or answer is invented. An empty or inconsistent trace stops the pipeline for investigation.

For an older pipeline process that stopped at the post-execution completeness check, only after verifying that process has actually terminated and all 162 main records exist, use `scripts/run_full_pipeline.py --continue-after-execution`. It skips the existing main actor grid, accounts for recorded failures, and continues the remaining phases. It refuses an active pipeline state and never silently fills an incomplete actor grid. Do not use it to rerun poor scores.

## Evidence and interpretation

Each run manifest records its full configuration, task selection, source hashes and tool-inventory hashes. Episode folders contain knowledge states, update evidence, raw model calls and tool results, and a fresh workspace. Before deferred judging, an immutable `agent-record.json` retains the actor result. Judging appends the rubric result to `result.json`.

Only after every expected episode has a valid score does aggregation produce the final summary. Inspect `analysis/completeness.json`, `analysis/episodes.csv` and `analysis/summary.json`. Development runs and calibration examples are not included in the formal means. Compare reported success with actual tool calls and files; a model's completion claim alone is insufficient evidence.

Run the independent protocol and paired-comparison checks after the full pipeline finishes:

```powershell
.venv/Scripts/python.exe scripts/audit_experiment.py runs/final-v1
.venv/Scripts/python.exe scripts/audit_experiment.py runs/ablation-v1
.venv/Scripts/python.exe scripts/analyze_comparisons.py runs/final-v1 --ablation runs/ablation-v1
.venv/Scripts/python.exe scripts/demo_evidence.py --task 28 --version iter3
```

The last command replays saved evidence without a model call and clearly labels it as a replay. It is useful for inspecting the update, calls and artifacts together. `paired-comparisons.json` includes independent arithmetic verification and stage-specific cohort denominators. Audit success establishes recorded protocol invariants, not semantic correctness of every answer.

The original pipeline uses a local subset and one repetition per configuration. Two later rounds were completed, but R2 has input-list differences and remains separate; the original-plus-R3 comparison has 18 distinct tasks and two observations per configuration. Neither a universal benchmark win nor statistical significance can be claimed. Local judge disagreement should be reported separately without rewriting scores to match the desired conclusion.

## Exporting the report figure

Before final packaging, verify the final workflow on held-out development task 3:

```powershell
.venv/Scripts/python.exe scripts/verify_final_workflow.py
```

This requires the formal pipeline to have completed and passed its audits. It runs nine development episodes (three methods × three versions), switches local models sequentially, scores and audits the saved traces, and checks that core source hashes match the formal run. Its directory is `runs/final-workflow-verification`. It is post-formal reproduction evidence only, excluded from benchmark statistics and method tuning. It refuses to overwrite an existing verification run. Earlier development runs used earlier source revisions and do not substitute for this check.

Use a separate optional report environment with `requirements-report.txt` installed; setup commands are given in the packaging section below. After all formal scores and aggregates exist:

```powershell
runtime/report-venv/Scripts/python.exe scripts/plot_results.py runs/final-v1 --output artifacts/figures
```

The script independently recomputes and checks scores before plotting; incomplete or unscored runs are rejected. It exports PNG, editable SVG and the exact plotted values in `figure-data.json`. The plot uses the full 1–10 score range and states the task and repetition counts. Development layout previews require `--development`, are visibly labeled, and belong in `tmp/`, not the submitted formal figures.

## Report and submission packaging

The PDF in the original release is the preserved original-round publication. To inspect a newly rendered report without replacing that historical PDF, use a separate report environment and a preview output:

```powershell
python -m venv runtime/report-venv
runtime/report-venv/Scripts/python.exe -m pip install -r requirements-report.txt
runtime/report-venv/Scripts/python.exe scripts/render_report.py docs/REPORT.md tmp/PE6203_Project4_Report-preview.pdf
```

Review the preview before publishing any new report. `scripts/build_submission.py` requires a Git checkout and selects source files from the Git-tracked list, including the archive. Review and stage or commit intended source changes first; untracked drafts, ignored local documents and the explicit internal-document exclusion list are not packaged. This Git filter applies to source collection only: the required ignored `runs/` evidence, events, failures and created/modified artifacts are still explicitly collected and verified.

The packager still checks the original main, component and development-verification runs; it is not a new three-round evidence archive builder. The two added rounds retain their separate Release packages. An existing `deliverables/PE6203_Project4_Submission.zip` is refused rather than overwritten. Existing release attachments remain historical evidence and are not replaced by documentation cleanup.

## Completed added rounds and archives

The completed added rounds are `repeat-r2-20261029` and `final-r3`. Each contains 162 scored episodes. The first has 123 cross-round resource-list differences and 54 within-round strategy-group differences; it is reported independently. Only the original and final-r3 satisfy the disclosed actual-input and scoring-condition comparison, giving 324 observations over 18 distinct tasks, not three comparable repetitions.

The experiment branch contains `repeat_preflight.py`, `repeat_runner.py` and `repeat_campaign.py` for prechecks and sequential execution; `repeat_common.py`, `repeat_pair_comparison.py` and `repeat_verify_archive.py` support completeness, comparison and archive verification. These helpers do not replace the frozen actor/updater core. Their completed campaign state and existing evidence must not be restarted just to view results. Inspect the saved metrics, pair index and Releases through the final-results page; a fresh repeat study must use separately prepared output directories and documented runtime conditions.

The [early development archive](../archive/development/README.md) contains the old task101 configuration and task3 pilot source, preserved for history rather than execution from their relocated paths. Ten partial progress snapshots are in the [experiment-branch progress archive](https://github.com/lingenxin3-sketch/pe6203-tool-harness-adaptation/blob/experiments/repeats-20261029/archive/progress/repeats-20261029/README.md). Archive manifests map old paths to new paths and distinguish original Git blob hashes from local-byte SHA-256. Historical receipts and old ZIPs retain their original paths and are not rewritten.

## Judge capacity amendment

Complete pre-scoring inspection found four main prompts exceeding the original 16,384-token reserved budget (largest estimate 20,317). The formal judge uses 24,576 tokens uniformly, as recorded in `configs/judge-capacity.json`. Use `scripts/judge_with_capacity.py RUN_DIRECTORY` for scoring. It checks the live server capacity, preserves the official prompt and all actor evidence, records the amendment, and skips existing evaluated records. Actor/updater capacity remains 16,384; core source is unchanged.

The completed formal run experienced two judge allocation interruptions, documented in the report and archived incident evidence. Same-configuration resumptions preserved all previously scored records. For a future terminal failed scoring pipeline, first verify its process has exited, preserve its logs, and then use .venv/Scripts/python.exe scripts/resume_scoring.py only after diagnosing the cause. It scores remaining awaiting-judge records and aggregates, refusing an active pipeline or incomplete actor evidence. Fresh pipeline runs use the capacity adapter from the start. Do not rerun this command on the completed evidence directory.
