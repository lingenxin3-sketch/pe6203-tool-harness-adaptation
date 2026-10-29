"""A real development task; excluded from subsequent final evaluation."""
import asyncio
import json
from pathlib import Path
import shutil
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tool_adapt.agent import run_agent
from tool_adapt.knowledge import Knowledge
from tool_adapt.llm import LocalModel
from tool_adapt.mcp_runtime import MCPRuntime, public_name

ROOT = Path(__file__).resolve().parents[1]


async def main():
    cases = json.loads((ROOT/'upstream/src/custom/data/test_cases/test_cases.json').read_text(encoding='utf-8'))
    case = next(case for case in cases if case['idx'] == 3)
    run = ROOT/'runs'/'pilot-case3-resource-list'
    workspace = run/'workspace'
    if run.exists():
        raise FileExistsError('Pilot output already exists; preserve evidence, choose a new run directory')
    shutil.copytree(ROOT/'upstream/anotation_path', workspace)
    # Preserve the original question and provide resource paths through the system environment.
    async with MCPRuntime(ROOT, 'original', list(case['servers']), workspace) as runtime:
        allowed = {public_name(server, name) for server, names in case['servers'].items() for name in names}
        tools = [tool for tool in runtime.tools if tool['name'] in allowed]
        knowledge = Knowledge.initial(tools)
        model = LocalModel(max_tokens=2048)
        result = await run_agent(model, runtime, knowledge, case['question'], max_steps=12)
        result.update({'idx': case['idx'], 'servers': case['servers'], 'split': 'development',
                       'knowledge': knowledge.to_dict(), 'model_calls': model.calls})
        (run/'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'idx':case['idx'],'finished':result['stop'],'calls':len(model.calls),
                          'errors':len(result['tool_errors']),'answer':result['answer']},ensure_ascii=True),flush=True)


if __name__ == '__main__':
    asyncio.run(main())
