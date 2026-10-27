"""Portability bridge to unmodified upstream scoring functions.

The upstream evaluation module imports a missing module and connects to a fixed
MCP port at import time. Load its pure functions verbatim via AST instead, and
provide captured current contracts. No rubric or score formula is rewritten.
"""
from __future__ import annotations
import ast
import importlib.util
import json
from pathlib import Path
import random
import sys
import typing


def load_file(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_pure_functions(path: Path, names: list[str]):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    nodes = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names]
    if {node.name for node in nodes} != set(names):
        raise ValueError('Upstream function layout changed')
    namespace = {**vars(typing), 'json': json, 'random': random}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)
    return namespace


class OfficialEvaluator:
    def __init__(self, upstream: Path):
        self.prompt = load_file(upstream/'src/custom/prompt/eval_error_prompt.py', 'mcpevol_official_prompt')
        self.ecs = load_file(upstream/'src/custom/analysis/answer/evolutionary_volatility.py', 'mcpevol_official_ecs')
        self.functions = load_pure_functions(upstream/'src/custom/analysis/answer/evaluation.py',
            ['messages_to_string', 'truncate_tool_content', '_mean_int', 'aggregate_eval_runs'])
        self.formatters = load_pure_functions(upstream/'src/custom/utils/test_utils.py', ['format_tools_to_string'])

    def judge(self, case, actual_tools, model, *, repeats=1, seed=6203):
        rng, runs, usages = random.Random(seed), [], []
        tools_text = self.formatters['format_tools_to_string'](actual_tools, dict_flag=True)
        trajectory = self.functions['truncate_tool_content'](case['trajectory_messages'])[2:]
        trajectory_text = self.functions['messages_to_string'](trajectory)
        for attempt in range(repeats * 3):
            order = [0, 1, 2]
            rng.shuffle(order)
            prompt = self.prompt.build_mcp_bench_judge_prompt(case['question'], tools_text,
                trajectory_text, case['answer'], dimension_order=tuple(order))
            message, usage = model.complete([{'role': 'user', 'content': prompt}], json_mode=True)
            usages.append(usage)
            try:
                parsed = json.loads(message['content'])
                for metric in ['task_fulfillment', 'grounding', 'planning_and_efficiency']:
                    if type(parsed.get(metric)) is not int or not 1 <= parsed[metric] <= 10:
                        raise ValueError('Missing or invalid judge score: ' + metric)
                runs.append({'result': parsed, 'dimension_order': order})
            except (ValueError, TypeError) as exc:
                runs.append({'result': {'error': str(exc), 'raw': message.get('content')}, 'dimension_order': order})
            if sum('error' not in run['result'] for run in runs) >= repeats:
                break
        aggregate = self.functions['aggregate_eval_runs'](runs)
        return {'runs': runs, 'aggregate': aggregate, 'usage': usages,
                'valid': aggregate['successful_runs'] >= repeats,
                'protocol': 'official rubric and pure aggregation; local model; captured current tool contracts'}
