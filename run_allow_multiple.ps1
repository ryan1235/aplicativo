$ErrorActionPreference = "Stop"

$env:FELB_ALLOW_MULTIPLE = "1"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

Push-Location $PSScriptRoot
try {
    if (Test-Path -LiteralPath $python) {
        & $python felb_app.py @args
    } else {
        & py felb_app.py @args
    }
} finally {
    Pop-Location
}
