param(
    [ValidateSet('demo', 'live')][string]$Mode = 'demo',
    [ValidateRange(1, 65535)][int]$Port = 8501,
    [switch]$NoBrowser,
    [switch]$Check
)

$ErrorActionPreference = 'Stop'
$atlasArguments = @((Join-Path $PSScriptRoot 'launch.py'), '--mode', $Mode, '--port', "$Port")
if ($NoBrowser) { $atlasArguments += '--no-browser' }
if ($Check) { $atlasArguments += '--check' }
$atlasVenvPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
$atlasExitCode = 1
Push-Location -LiteralPath $PSScriptRoot
try {
    if (Test-Path -LiteralPath $atlasVenvPython) {
        & $atlasVenvPython @atlasArguments
    } elseif (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 @atlasArguments
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python @atlasArguments
    } else {
        throw 'Python 3.11+ is required. Install Python, create .venv, then install requirements.txt.'
    }
    $atlasExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $atlasExitCode
