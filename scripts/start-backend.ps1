$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'The project Python environment is missing. Follow README.md to install dependencies.'
}
Set-Location -LiteralPath $projectRoot
Write-Host 'Starting SkillForge AI at http://127.0.0.1:8000. Keep this terminal open.'
Write-Host 'Provider keys are read from backend/.env. Press Ctrl+C to stop.'
& $pythonPath backend\manage.py runserver 127.0.0.1:8000 --noreload
exit $LASTEXITCODE
