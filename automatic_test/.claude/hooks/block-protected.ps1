# PreToolUse hook: block edits to secrets (.env) and the local SQLite DB.
# Exit 2 = block the tool call and surface stderr back to Claude.

$ErrorActionPreference = 'Stop'

try {
    $payload = [Console]::In.ReadToEnd() | ConvertFrom-Json
    $path = $payload.tool_input.file_path
} catch {
    # If we cannot parse the payload, do not block.
    exit 0
}

if (-not $path) { exit 0 }

if ($path -match '\.env$' -or $path -match 'autotest\.db$' -or $path -match '\\data\\.*\.db$') {
    [Console]::Error.WriteLine("BLOCKED: '$path' is a protected file (.env / SQLite DB). Edit manually if truly intended.")
    exit 2
}

exit 0
