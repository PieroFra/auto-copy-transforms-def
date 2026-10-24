# run_ui_probe.ps1 — verifica UI A.C.T.D. in un colpo solo.
#
# 1. avvia Blender in modalita' GUI con il ponte TCP (dietro le altre finestre);
# 2. esegue actd_ui_probe.py dentro Blender;
# 3. chiude il ponte (solo il PID avviato qui).
#
# Output: report UI_TEXT/UI_SUMMARY (misure deterministiche) + 2 PNG ritagliati
# in %TEMP%\opencode\actd_gui\ : actd-ui-it.png e actd-ui-en.png (max 1024 px di larghezza).
param([int]$Port = 9878)

$ErrorActionPreference = 'Stop'
$env:BLENDER_BRIDGE_PORT = "$Port"
$env:PYTHONIOENCODING = 'utf-8'

$blender = 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
$py = 'C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe'

# Cartella degli script del bridge: derivata da $PSScriptRoot
# (.opencode/scripts -> .opencode -> skills/blender-bridge/scripts), con fallback
# risalendo i livelli finche' non si trova blender_bridge.py.
$scripts = $null
$base = $PSScriptRoot
for ($i = 0; $i -lt 5; $i++) {
  $parent = Split-Path -Parent $base
  if (-not $parent) { break }
  $candidate = Join-Path $parent 'skills\blender-bridge\scripts'
  if (Test-Path (Join-Path $candidate 'blender_bridge.py')) { $scripts = $candidate; break }
  $base = $parent
}
if (-not $scripts) { $scripts = Join-Path (Split-Path -Parent $PSScriptRoot) 'skills\blender-bridge\scripts' }

# Ancora per i moduli Python eseguiti dentro Blender (che non hanno __file__)
$env:ACTD_SCRIPTS_DIR = $scripts

if (-not (Test-Path $blender)) { throw "Blender non trovato: $blender" }

$proc = Start-Process -FilePath $blender `
  -ArgumentList @('--factory-startup', '--no-window-focus', '--python', ('"' + (Join-Path $scripts 'blender_bridge.py') + '"')) `
  -PassThru -WindowStyle Hidden

$probeExit = 0
try {
  $ready = $false
  for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 1
    if (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue) { $ready = $true; break }
  }
  if (-not $ready) { throw "Ponte Blender non in ascolto sulla porta $Port" }
  & $py (Join-Path $scripts 'bridge_call.py') (Join-Path $scripts 'actd_ui_probe.py')
  $probeExit = $LASTEXITCODE
}
finally {
  # si chiude solo il Blender avviato da questo script
  Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
}

# --- check geometrico deterministico (0 token di visione) --------------------
# Il Visualizzatore deve potersi fermare PRIMA di guardare i PNG: se il
# report ha righe TIGHT o i PNG sono neri/corrotti, il verdetto e' gia' FAIL
# e i token di vision sono sprecati. Il codice decide, non il modello.
$outDir = Join-Path ([IO.Path]::GetTempPath()) 'opencode\actd_gui'
$mathCheck = Join-Path $PSScriptRoot 'ui_math_check.py'
if (Test-Path $mathCheck) {
  & $py $mathCheck $outDir
  $mathExit = $LASTEXITCODE
  if ($mathExit -ne 0) {
    Write-Output 'UI_PROBE_FAIL | stage=math_check'
    exit 1
  }
}
exit $probeExit
