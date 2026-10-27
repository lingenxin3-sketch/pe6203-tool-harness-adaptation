import argparse
import asyncio
from pathlib import Path
from .experiment import run_experiment, judge_experiment
from .results import aggregate


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description='MCPEvol-Bench selective tool adaptation')
    sub = parser.add_subparsers(dest='command', required=True)
    run = sub.add_parser('run')
    run.add_argument('--config', type=Path, default=root/'configs/experiment.json')
    run.add_argument('--output', type=Path, required=True)
    run.add_argument('--split', choices=['development', 'test'], default='development')
    run.add_argument('--task-limit', type=int)
    analyze = sub.add_parser('analyze')
    analyze.add_argument('run_directory', type=Path)
    judge = sub.add_parser('judge')
    judge.add_argument('run_directory', type=Path)
    args = parser.parse_args()
    if args.command == 'run':
        asyncio.run(run_experiment(root, args.config, args.output.resolve(), split=args.split, task_limit=args.task_limit))
    elif args.command == 'analyze':
        import json
        print(json.dumps(aggregate(root,args.run_directory.resolve()),ensure_ascii=False,indent=2))
    elif args.command == 'judge':
        judge_experiment(root,args.run_directory.resolve())


if __name__ == '__main__':
    main()
