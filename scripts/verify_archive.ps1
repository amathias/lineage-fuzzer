param(
    [string]$Commit = "HEAD",
    [string]$PythonExecutable = "python",
    [string]$ScratchRoot = ""
)

$ErrorActionPreference = "Stop"
$repository = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($ScratchRoot)) {
    $ScratchRoot = Join-Path ([System.IO.Path]::GetTempPath()) (
        "lineage-fuzzer-archive-" + [System.Guid]::NewGuid().ToString("N")
    )
}
$scratch = [System.IO.Path]::GetFullPath($ScratchRoot)
$source = Join-Path $scratch "source"
$archive = Join-Path $scratch "source.tar"
New-Item -ItemType Directory -Path $source -Force | Out-Null

& git -C $repository archive --format=tar --output=$archive $Commit
if ($LASTEXITCODE -ne 0) { throw "git archive failed" }
& tar -xf $archive -C $source
if ($LASTEXITCODE -ne 0) { throw "archive extraction failed" }

Push-Location $source
try {
    & $PythonExecutable scripts/scan_secrets.py
    if ($LASTEXITCODE -ne 0) { throw "secret scan failed" }

    & $PythonExecutable -m venv .verify-venv
    if ($LASTEXITCODE -ne 0) { throw "virtual environment creation failed" }
    $python = Join-Path $source ".verify-venv/Scripts/python.exe"
    if (-not (Test-Path $python)) {
        $python = Join-Path $source ".verify-venv/bin/python"
    }
    & $python -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }
    & $python -m pip install ".[dev,datahub]"
    if ($LASTEXITCODE -ne 0) { throw "isolated dependency install failed" }

    $dist = Join-Path $source ".verify-dist"
    & $python -m pip wheel . --no-deps --wheel-dir $dist
    if ($LASTEXITCODE -ne 0) { throw "wheel build failed" }
    $wheel = Get-ChildItem -LiteralPath $dist -Filter "lineage_fuzzer-*.whl" |
        Select-Object -First 1
    if ($null -eq $wheel) { throw "Lineage Fuzzer wheel was not produced" }
    & $python -m pip install --force-reinstall --no-deps $wheel.FullName
    if ($LASTEXITCODE -ne 0) { throw "built wheel installation failed" }

    & $python -c "import datahub, lineage_fuzzer, mcp; print(lineage_fuzzer.__version__)"
    if ($LASTEXITCODE -ne 0) { throw "installed-package import smoke failed" }
    & $python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "archive tests failed" }
    & $python -m ruff check src tests scripts
    if ($LASTEXITCODE -ne 0) { throw "archive lint failed" }

    & $python -m lineage_fuzzer.pipeline_cli seed
    if ($LASTEXITCODE -ne 0) { throw "fixture seed smoke failed" }
    & $python -m lineage_fuzzer.pipeline_cli controls
    if ($LASTEXITCODE -ne 0) { throw "fixture controls smoke failed" }
    & $python -c "from fastapi.testclient import TestClient; from lineage_fuzzer.api import create_app; c=TestClient(create_app()); assert c.get('/').status_code == 200; p=c.get('/api/demo/plan'); assert p.status_code == 200; assert len(p.json()['graph']['nodes']) == 6"
    if ($LASTEXITCODE -ne 0) { throw "judge UI smoke failed" }

    Write-Output (
        "verified_archive commit=$Commit source=$source wheel=$($wheel.Name)"
    )
}
finally {
    Pop-Location
}
