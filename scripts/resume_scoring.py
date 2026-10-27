"""Continue deferred scoring after a verified terminal pipeline failure.

Never executes an actor or overwrites an existing score. The caller must first
confirm that the original process handle has terminated.
"""
import json
from run_full_pipeline import ROOT, STATE, MAIN, ABLATION, state, shell_script, health, command
from audit_experiment import audit


if __name__ == '__main__':
    previous = json.loads(STATE.read_text(encoding='utf-8'))
    if previous['phase'] != 'failed':
        raise RuntimeError('Requires a terminal failed pipeline; never run alongside the active pipeline')
    for folder in [MAIN, ABLATION]:
        report = audit(folder)
        if not report['recorded_invariants_pass'] or report['found'] != report['expected']:
            raise RuntimeError(f'Complete unchanged actor evidence required: {folder.name}')
    try:
        state('switch_to_judge')
        shell_script('stop-local-model.ps1', '-Role', 'actor')
        shell_script('start-judge.ps1'); health(8082)
        state('main_judging')
        command('formal-judging-continuation.log', 'judge', MAIN)
        state('ablation_judging')
        command('ablation-judging-continuation.log', 'judge', ABLATION)
        state('aggregation')
        command('formal-summary.log', 'analyze', MAIN)
        command('ablation-summary.log', 'analyze', ABLATION)
        state('completed')
    except Exception as exc:
        state('failed', error=type(exc).__name__+': '+str(exc))
        raise
