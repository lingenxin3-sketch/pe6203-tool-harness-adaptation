"""Offline judge-vocabulary preflight; no model generation or score changes.

Tokenizes the actual official rubric prompt with the downloaded judge vocabulary.
Adds a conservative chat-template allowance. The live judge still performs its
own exact template/context check. --longest 0 checks all available records.
"""
import argparse
import ast
import json
from pathlib import Path
import random
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tool_adapt.official import OfficialEvaluator


def check(folder, longest):
    config = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))['config']
    evaluator = OfficialEvaluator(ROOT/'upstream')
    prompts = []
    for path in folder.glob('repeat-*/*/*/*/result.json'):
        record = json.loads(path.read_text(encoding='utf-8'))
        if 'trajectory_messages' not in record:
            continue
        tools = evaluator.formatters['format_tools_to_string'](record['evaluation_tools'], dict_flag=True)
        trajectory = evaluator.functions['messages_to_string'](
            evaluator.functions['truncate_tool_content'](record['trajectory_messages'])[2:])
        order = [0, 1, 2]
        random.Random(config['seed']+record['idx']).shuffle(order)
        prompt = evaluator.prompt.build_mcp_bench_judge_prompt(record['question'], tools, trajectory,
                                                               record['answer'], dimension_order=tuple(order))
        prompts.append((len(prompt), path.relative_to(folder).as_posix(), prompt))
    prompts.sort(reverse=True)
    candidates = prompts[:longest] if longest else prompts
    results = []
    for chars, path, prompt in candidates:
        completed = subprocess.run([str(ROOT/'runtime/llama/llama-tokenize.exe'), '-m',
            str(ROOT/'runtime/downloads/qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf'),
            '--stdin', '--ids', '--no-bos', '-ngl', '0'], input=prompt,
            capture_output=True, text=True, encoding='utf-8', errors='strict', check=True)
        tokens = len(ast.literal_eval(completed.stdout.strip()))
        reserved = tokens+config['judge_max_tokens']+128+256
        results.append({'record': path, 'prompt_characters': chars, 'content_tokens': tokens,
                        'with_response_safety_and_template_allowance': reserved,
                        'fits_16384_with_allowance': reserved <= 16384})
    report = {'available_records': len(prompts), 'checked_records': len(results),
              'selection': 'All available' if not longest else f'Longest {longest} by prompt characters; not exhaustive',
              'model_vocabulary': 'Qwen2.5-7B-Instruct Q4_K_M downloaded judge',
              'template_allowance_tokens': 256, 'safety_tokens': 128,
              'no_inference': True, 'results': results,
              'limitation': 'Raw prompt token count plus an allowance; exact chat-template validation remains at live judging.'}
    output = folder/'analysis/judge-context-preflight.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path)
    parser.add_argument('--longest', type=int, default=8)
    args = parser.parse_args()
    report = check(args.run_directory.resolve(), args.longest)
    print(json.dumps(report, indent=2))
