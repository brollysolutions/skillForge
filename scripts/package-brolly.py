"""Package source and the subpath build, excluding credentials and classroom data."""
import hashlib
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
build = root / 'frontend' / 'dist-brolly'
if not (build / 'index.html').is_file():
    raise SystemExit('Build the frontend first: npm run build:brolly (or build:brolly:portable).')
output = root / 'artifacts' / 'skillforge-brolly.zip'
output.parent.mkdir(exist_ok=True)
files = set()
for name in ['backend', 'frontend/src', 'frontend/dist-brolly', 'infra', 'scripts', 'docs']:
    for path in (root / name).rglob('*'):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if relative.parts[0] == 'backend' and path.suffix != '.py' and path.name not in {'requirements.txt', '.env.example', 'Dockerfile'}:
            continue
        if {'__pycache__', 'media', 'staticfiles', 'node_modules'} & set(relative.parts):
            continue
        if path.name == '.env' or path.name.endswith('.local') or path.suffix in {'.sqlite3', '.pyc', '.log'}:
            continue
        if not path.resolve().is_relative_to(root):
            raise SystemExit('Refusing to package a file outside the workspace.')
        files.add(path)
for name in ['README.md', '.gitignore', '.dockerignore', '.env.example', 'docker-compose.yml',
             'frontend/Dockerfile', 'frontend/package.json', 'frontend/package-lock.json',
             'frontend/index.html', 'frontend/vite.config.js', 'frontend/vite.portable.config.js',
             'frontend/.env.example', 'frontend/.env.brolly']:
    path = root / name
    if path.is_file():
        files.add(path)
for path in (root / 'frontend' / 'scripts').glob('*.mjs'):
    files.add(path)
with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(files):
        archive.write(path, path.relative_to(root).as_posix())
digest = hashlib.sha256(output.read_bytes()).hexdigest()
output.with_suffix('.zip.sha256').write_text(f'{digest}  {output.name}\n')
print(f'Packaged {len(files)} files: {output}')
print(f'SHA256: {digest}')
