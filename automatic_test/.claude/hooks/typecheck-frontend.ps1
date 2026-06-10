# PostToolUse hook: run vue-tsc only when a frontend .vue/.ts file was edited.
# Reports the last 20 lines of output so type errors surface to Claude.
# Exits 0 always (non-blocking) — output is informational.

$ErrorActionPreference = 'SilentlyContinue'

try {
    $payload = [Console]::In.ReadToEnd() | ConvertFrom-Json
    $path = $payload.tool_input.file_path
} catch {
    exit 0
}

if (-not $path) { exit 0 }

# Normalize backslashes for matching
$normalized = $path -replace '\\', '/'

if ($normalized -notmatch 'frontend/.*\.(vue|ts|tsx)$') {
    exit 0
}

# Run type-check from the frontend directory
$frontend = Join-Path $PSScriptRoot '..\..\frontend'
if (-not (Test-Path $frontend)) { exit 0 }

Push-Location $frontend
try {
    $output = & npx --no-install vue-tsc --noEmit 2>&1 | Select-Object -Last 20
    if ($LASTEXITCODE -ne 0 -and $output) {
        Write-Host "vue-tsc reported issues after editing $path :"
        $output | ForEach-Object { Write-Host $_ }
    }
} finally {
    Pop-Location
}

exit 0
