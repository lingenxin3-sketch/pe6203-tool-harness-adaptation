"""Extract selected official npm packages and their archived dependencies unchanged."""
from pathlib import Path, PurePosixPath
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ['mcp-filesystem-server', 'mcp-tasks', 'mcp-shrimp-task-manager',
            '@modelcontextprotocol/server-filesystem', '@kazuph/mcp-taskmanager',
            'time-mcp', 'mcp-sequentialthinking-tools', '@modelcontextprotocol/server-sequential-thinking',
            '@pimzino/agentic-tools-mcp', '@modelcontextprotocol/server-memory', '@itseasy21/mcp-knowledge-graph']


def prepare(version):
    archive = ROOT / 'runtime' / 'downloads' / f'{version}_servers.zip'
    destination = (ROOT / 'runtime' / 'servers' / version).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        paths = set(z.namelist())
        pending = ['node_modules/' + package for package in PACKAGES]
        selected, missing = set(), set()
        while pending:
            package = pending.pop()
            if package in selected:
                continue
            metadata = package + '/package.json'
            if metadata not in paths:
                missing.add(package)
                continue
            selected.add(package)
            data = json.loads(z.read(metadata))
            dependencies = dict(data.get('dependencies', {}))
            dependencies.update(data.get('optionalDependencies', {}))
            for dep in dependencies:
                # Resolve nested dependencies first, as Node does.
                base = PurePosixPath(package)
                candidates = []
                while str(base) != '.':
                    if base.name != 'node_modules':
                        candidates.append(str(base / 'node_modules' / dep))
                    base = base.parent
                candidates.append('node_modules/' + dep)
                found = next((candidate for candidate in candidates if candidate + '/package.json' in paths), None)
                if found:
                    pending.append(found)
                elif dep not in data.get('optionalDependencies', {}):
                    missing.add(package + ' -> ' + dep)
        prefixes = tuple(package + '/' for package in selected)
        count = 0
        for info in z.infolist():
            if info.is_dir() or not info.filename.startswith(prefixes):
                continue
            relative = PurePosixPath(info.filename)
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('Unsafe archive member')
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists() or target.stat().st_size != info.file_size:
                target.write_bytes(z.read(info))
            count += 1
        result = {'version': version, 'packages': sorted(selected), 'missing': sorted(missing),
                  'files': count, 'source': str(archive), 'modified_server_source': False}
        (destination / 'extraction.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(version, 'files', count, 'packages', len(selected), 'missing', sorted(missing), flush=True)


if __name__ == '__main__':
    for version in ['original', 'iter3', 'iter5']:
        prepare(version)
