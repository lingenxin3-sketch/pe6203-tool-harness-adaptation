"""Inventory actual official server contracts before choosing any experiment tasks."""
import asyncio
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tool_adapt.mcp_runtime import MCPRuntime

ROOT = Path(__file__).resolve().parents[1]
SERVERS = ['mcp-filesystem-server', 'mcp-tasks', 'mcp-shrimp-task-manager',
           '@modelcontextprotocol/server-filesystem', '@kazuph/mcp-taskmanager',
           'time-mcp', 'mcp-sequentialthinking-tools', '@modelcontextprotocol/server-sequential-thinking',
           '@pimzino/agentic-tools-mcp', '@modelcontextprotocol/server-memory', '@itseasy21/mcp-knowledge-graph']

async def main():
    output = ROOT / 'artifacts' / 'inventory'
    output.mkdir(parents=True, exist_ok=True)
    for version in ['original', 'iter3', 'iter5']:
        inventory = {}
        for server in SERVERS:
            try:
                async with MCPRuntime(ROOT, version, [server], ROOT/'runtime'/'probe'/version/server.replace('/', '_')) as runtime:
                    inventory[server] = {'status': 'ok', 'tools': runtime.tools, 'routing': runtime.routing}
                    print(version, server, len(runtime.tools), 'tools', flush=True)
            except BaseException as exc:
                if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                    raise
                inventory[server] = {'status': 'failed', 'error': str(exc)}
                print(version, server, 'FAILED', str(exc)[:200], flush=True)
            (output/f'{version}.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding='utf-8')

if __name__ == '__main__':
    asyncio.run(main())
