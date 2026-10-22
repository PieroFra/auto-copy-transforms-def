param(
    [string]$Blender = 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
)

# Costruisce lo ZIP dell'estensione partendo dal file singolo dell'addon.
$ErrorActionPreference = 'Stop'

$root = Split-Path $PSScriptRoot -Parent
$stage = Join-Path $env:TEMP ('actd_ext_build_' + [guid]::NewGuid().ToString('N'))
$dist = Join-Path $root 'dist'
$zip = Join-Path $dist 'auto_copy_transforms_def-1.1.3.zip'

New-Item -ItemType Directory -Path $stage -Force | Out-Null
New-Item -ItemType Directory -Path $dist -Force | Out-Null

Copy-Item -LiteralPath (Join-Path $root 'actd_build\auto_copy_transforms_def.py') `
    -Destination (Join-Path $stage '__init__.py')
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
