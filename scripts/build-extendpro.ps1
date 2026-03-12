$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $repoRoot ".extendpro.env"

if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            return
        }

        $parts = $line -split "=", 2
        if ($parts.Count -ne 2) {
            return
        }

        [System.Environment]::SetEnvironmentVariable($parts[0], $parts[1], "Process")
    }
}

if (-not $env:HUGGINGFACE_ACCESS_TOKEN) {
    throw "HUGGINGFACE_ACCESS_TOKEN is required. Set it in .extendpro.env or the shell environment."
}

docker buildx bake extendpro --load
