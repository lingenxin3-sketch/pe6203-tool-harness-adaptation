"""Run archived official MCP servers directly, preserving server implementation."""
from __future__ import annotations
import asyncio
from contextlib import AsyncExitStack
import hashlib
import json
import os
from pathlib import Path
import shutil
from datetime import timedelta
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def public_name(server, tool):
    return hashlib.sha256(server.encode()).hexdigest()[:6] + '__' + tool


class MCPRuntime:
    def __init__(self, root: Path, version: str, servers: list[str], workspace: Path, timeout=45):
        self.root, self.version = root.resolve(), version
        self.servers, self.workspace = sorted(servers), workspace.resolve()
        self.timeout = timeout
        self.stack = AsyncExitStack()
        self.sessions, self.routing, self.tools = {}, {}, []

    async def __aenter__(self):
        self.workspace.mkdir(parents=True, exist_ok=True)
        try:
            for server in self.servers:
                package = self.root / 'runtime' / 'servers' / self.version / 'node_modules' / server
                metadata = json.loads((package / 'package.json').read_text(encoding='utf-8'))
                binary = metadata.get('bin')
                if isinstance(binary, dict):
                    binary = next(iter(binary.values()))
                if not binary:
                    raise ValueError(f'No executable entrypoint: {server}')
                args = ['--import', (self.root / 'scripts' / 'windows_loader.mjs').as_uri(), str(package / binary)]
                if server == '@modelcontextprotocol/server-filesystem':
                    args.append(str(self.workspace))
                env = dict(os.environ)
                env.update({'DATA_DIR': str(self.workspace / 'shrimp'),
                            'TASK_MANAGER_FILE_PATH': str(self.workspace / 'tasks.json'),
                            'SOURCES_PATH': str(self.workspace / 'sources.json'),
                            'WORKSPACE_FOLDER_PATHS': str(self.workspace),
                            'MEMORY_FILE_PATH': str(self.workspace / 'memory.jsonl'),
                            'ENABLE_GUI': 'false', 'MAX_HISTORY_SIZE': '1000'})
                stderr = self.stack.enter_context((self.workspace / (hashlib.sha256(server.encode()).hexdigest()[:8] + '.stderr.log')).open('a', encoding='utf-8'))
                params = StdioServerParameters(command=shutil.which('node') or 'node', args=args,
                                                env=env, cwd=str(self.workspace))
                read, write = await self.stack.enter_async_context(stdio_client(params, errlog=stderr))
                session = await self.stack.enter_async_context(ClientSession(read, write,
                    read_timeout_seconds=timedelta(seconds=self.timeout)))
                await asyncio.wait_for(session.initialize(), timeout=self.timeout)
                listing = await asyncio.wait_for(session.list_tools(), timeout=self.timeout)
                self.sessions[server] = session
                for tool in listing.tools:
                    name = public_name(server, tool.name)
                    if len(name) > 64 or name in self.routing:
                        raise ValueError('Invalid or duplicate tool alias: ' + name)
                    self.routing[name] = (server, tool.name)
                    self.tools.append({'name': name, 'description': tool.description or '',
                                       'inputSchema': tool.inputSchema or {}})
            return self
        except BaseException:
            await self.stack.aclose()
            raise

    async def __aexit__(self, *args):
        return await self.stack.__aexit__(*args)

    async def call(self, name, arguments):
        if name not in self.routing:
            return {'isError': True, 'content': [{'type': 'text', 'text': 'Tool does not exist in the current environment: ' + name}]}
        server, actual = self.routing[name]
        error = self.path_violation(arguments)
        if error:
            return {'isError': True, 'content': [{'type': 'text', 'text': error}]}
        try:
            result = await self.sessions[server].call_tool(actual, arguments)
            return result.model_dump(mode='json', exclude_none=True)
        except Exception as exc:
            return {'isError': True, 'content': [{'type': 'text', 'text': type(exc).__name__ + ': ' + str(exc)}]}

    def path_violation(self, value, key=''):
        """Keep file operations inside each independent experiment workspace."""
        if isinstance(value, dict):
            for field, item in value.items():
                error = self.path_violation(item, field)
                if error:
                    return error
        elif isinstance(value, list):
            for item in value:
                error = self.path_violation(item, key)
                if error:
                    return error
        elif isinstance(value, str) and (any(part in key.lower() for part in ('path', 'directory', 'filename')) or key.lower() in {'source', 'destination', 'cwd', 'workingdirectory'}):
            candidate = (self.workspace / value).resolve()
            if not candidate.is_relative_to(self.workspace):
                return 'File operations must stay inside the experiment workspace: ' + str(self.workspace)
        return None
