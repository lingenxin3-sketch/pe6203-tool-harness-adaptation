"""Judge-only capacity adapter; frozen actor/updater source remains unchanged.

The complete official prompt is preserved. Only the client capacity guard is
expanded to match the uniformly configured judge server. Existing valid scores
are skipped by the original deferred scorer, never regenerated.
"""
import argparse
import json
from pathlib import Path
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tool_adapt import experiment


def expand_capacity(model, capacity):
    original_fit = model.fit_context
    def fit(body):
        fitted, evidence = original_fit(body, context_size=capacity)
        evidence['context_limit'] = capacity
        evidence['capacity_policy'] = 'configs/judge-capacity.json'
        return fitted, evidence
    model.fit_context = fit
    return model


def judge(folder):
    policy = json.loads((ROOT/'configs/judge-capacity.json').read_text(encoding='utf-8'))
    config = experiment.read(folder/'manifest.json')['config']
    endpoint = config['judge_base_url'].removesuffix('/v1')
    with urllib.request.urlopen(endpoint+'/props', timeout=10) as response:
        properties = json.load(response)
    actual = properties.get('default_generation_settings', {}).get('n_ctx')
    if actual != policy['context_tokens']:
        raise RuntimeError(f'Judge server context must be {policy["context_tokens"]}, found {actual}')
    destination = folder/'analysis/judge-capacity.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    evidence = {'policy': policy, 'server_context': actual,
                'adapter_sha256': __import__('hashlib').sha256(Path(__file__).read_bytes()).hexdigest()}
    if destination.exists() and experiment.read(destination) != evidence:
        raise RuntimeError('Existing judge capacity receipt differs; do not overwrite')
    experiment.save(destination, evidence)
    original_factory = experiment.model_from
    def factory(settings, kind):
        model = original_factory(settings, kind)
        if kind != 'judge':
            raise RuntimeError('Capacity adapter may only construct a judge')
        return expand_capacity(model, policy['context_tokens'])
    experiment.model_from = factory
    try:
        experiment.judge_experiment(ROOT, folder)
    finally:
        experiment.model_from = original_factory


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path)
    args = parser.parse_args()
    judge(args.run_directory.resolve())
