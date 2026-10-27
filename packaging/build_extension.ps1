param(
    [string]$Blender = 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
)

# Costruisce lo ZIP dell'estensione partendo dal pacchetto generato dalla build.
$ErrorActionPreference = 'Stop'

$root = Split-Path $PSScriptRoot -Parent
$stage = Join-Path ([System.IO.Path]::GetTempPath()) ('actd_ext_build_' + [guid]::NewGuid().ToString('N'))
$dist = Join-Path $root 'dist'

# Versione: unica fonte di verita' packaging\version.json (nessun numero qui).
$versionData = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'version.json') -Raw | ConvertFrom-Json
$ver = ($versionData.version -join '.')
$zip = Join-Path $dist ('auto_copy_transforms_def-' + $ver + '.zip')

# Pacchetto generato da packaging\build_package.py build: __init__.py + 9
# moduli copiati, tutti da mettere nella radice dello stage.
$pkg = Join-Path $root 'actd_build\auto_copy_transforms_def'
if (-not (Test-Path -LiteralPath $pkg -PathType Container)) {
    throw "Pacchetto generato non trovato: $pkg (eseguire: python packaging/build_package.py build)"
}

New-Item -ItemType Directory -Path $stage -Force | Out-Null
New-Item -ItemType Directory -Path $dist -Force | Out-Null

# Tutta la radice del pacchetto generato va nello stage (10 file .py).
Copy-Item -Path (Join-Path $pkg '*') -Destination $stage
Copy-Item -LiteralPath (Join-Path $root 'LICENSE') `
    -Destination (Join-Path $stage 'LICENSE.txt')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'blender_manifest.toml') `
    -Destination $stage
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'README.txt') `
    -Destination $stage
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'README.it.txt') `
    -Destination $stage

Remove-Item -LiteralPath $zip -Force -ErrorAction SilentlyContinue
& $Blender --background --factory-startup --command extension build `
    --source-dir $stage --output-filepath $zip
if ($LASTEXITCODE -ne 0) {
    throw "Build dell'estensione fallita."
}

& $Blender --background --factory-startup --command extension validate $zip
if ($LASTEXITCODE -ne 0) {
    throw "Validazione dell'estensione fallita."
}

Write-Host "Estensione creata: $zip"
