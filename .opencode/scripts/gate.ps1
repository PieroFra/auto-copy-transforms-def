# gate.ps1 — porta d'ingresso unica della verifica.
#
# Un solo comando, zero argomenti da ricordare, un solo output. Il verdetto
# non passa mai dalla prosa del modello: lo script esegue, verifica il
# proprio risultato contro la telemetria e stampa la riga finale.
#
# Uso (dal vivo):
#   powershell -NoProfile -ExecutionPolicy Bypass -File .opencode\scripts\gate.ps1
#
# Uso (con tag di correlazione, per l'Architetto):
#   powershell -NoProfile -ExecutionPolicy Bypass -File .opencode\scripts\gate.ps1 -TaskTag d1
#
# Exit code: 0 = VERIFY_OK, 1 = VERIFY_FAIL, 2 = errore d'uso.
param(
    [string]$TaskTag = "",
    [string]$Suites = "",
    # Soglia del diff: 150 era la soglia storica (anti-refactoring a tappeto),
    # poi 250, poi 600: la fase REPLACE (f4a) ha un diff legittimo di ~457
    # righe (operatori + test_mod6 + monolite generato).
    [int]$MaxDiffLines = 600,
    [switch]$AutoRollback,
    [int]$MaxAgeMin = 30,
    [string]$Agent = ""
)

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

$root = (Get-Item "$PSScriptRoot\..\..").FullName
$verify = Join-Path $PSScriptRoot "verify.ps1"
$audit = Join-Path $PSScriptRoot "audit_verdict.py"
$py = "C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe"

if (-not (Test-Path $py)) { throw "Python di Blender non trovato: $py" }
if (-not (Test-Path $verify)) { throw "verify.ps1 non trovato: $verify" }

# --- lock: una verifica alla volta -------------------------------------------
# verdict.txt e metrics.jsonl sono stato condiviso: due verifiche in
# contemporanea si scriverebbero l'una addosso all'altra e l'audit potrebbe
# confrontare un verdetto con la telemetria di un'altra run.
$lockFile = Join-Path $root ".opencode\gate.lock"
$lockDir = Split-Path -Parent $lockFile
if (-not (Test-Path $lockDir)) { New-Item -ItemType Directory -Path $lockDir -Force | Out-Null }
$lockStream = $null
try {
    $lockStream = [IO.File]::Open($lockFile, [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
} catch {
    Write-Output "VERIFY_FAIL | reason=LOCKED | lock=$lockFile | una verifica e' gia' in corso"
    exit 1
}

try {
    # Il tag serve a correlare il verdetto a QUESTA delega: senza, un verdict
    # di una run precedente potrebbe essere accettato come valido.
    if (-not $TaskTag) {
        $TaskTag = "gate-{0}" -f (Get-Date).ToString("HHmmss")
    }

    $verifyArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $verify,
                    "-TaskTag", $TaskTag, "-MaxDiffLines", "$MaxDiffLines")
    if ($Suites) { $verifyArgs += @("-Suites", $Suites) }
    if ($AutoRollback) { $verifyArgs += "-AutoRollback" }
    if ($Agent) { $verifyArgs += @("-Agent", $Agent) }

    $prevEA = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $out = & powershell @verifyArgs 2>&1
        $verifyExit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prevEA
    }

    $verdict = ""
    foreach ($line in $out) {
        $t = "$line".Trim()
        if ($t -match '^VERIFY_(OK|FAIL)') { $verdict = $t }
    }
    if (-not $verdict) {
        Write-Output "VERIFY_FAIL | reason=NO_VERDICT | task=$TaskTag | exit=$verifyExit"
        exit 1
    }

    # Auto-audit: il verdetto deve essere supportato da una run reale e coerente
    # con la telemetria. Se non lo e', il verdetto e' FAIL per principio.
    if (Test-Path $audit) {
        $auditArgs = @((Join-Path $PSScriptRoot "audit_verdict.py"), "--root", $root,
                       "--max-age-min", "$MaxAgeMin", "--expect-tag", $TaskTag)
        $prevEA = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            $auditOut = & $py @auditArgs 2>&1
            $auditExit = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $prevEA
        }
        $auditLine = ""
        foreach ($line in $auditOut) { $t = "$line".Trim(); if ($t -match '^AUDIT_') { $auditLine = $t } }
        if ($auditExit -ne 0) {
            # La ragione reale viene da verify.ps1: ha gia' stabilito cosa e'
            # andato storto (es. TESTS_FAILED con i conteggi). La riga dell'audit
            # dice solo se il verdetto e' supportato da una run reale.
            $realReason = "AUDIT"
            if ($verdict -match 'reason=([^|]+)') { $realReason = $Matches[1].Trim() }
            $auditReason = "FAILED"
            if ($auditLine -match 'reason=([^|]+)') { $auditReason = $Matches[1].Trim() }
            # Si conserva la riga di verify.ps1 (contiene passed/failed/expected):
            # e' l'informazione che serve per agire, e si aggiunge il verdetto audit.
            $extra = ""
            if ($verdict -match 'passed=(\d+)') { $extra += " passed=$($Matches[1])" }
            if ($verdict -match 'failed=(\d+)') { $extra += " failed=$($Matches[1])" }
            if ($verdict -match 'expected=(\d+)') { $extra += " expected=$($Matches[1])" }
            Write-Output "VERIFY_FAIL | reason=$realReason |$extra | audit=$auditReason | task=$TaskTag"
            exit 1
        }
    }

    # Il tag riportato deve essere quello di questa delega.
    if ($verdict -notmatch [regex]::Escape("task=$TaskTag")) {
        Write-Output "VERIFY_FAIL | reason=TAG_MISMATCH | task=$TaskTag | verdict=$verdict"
        exit 1
    }

    Write-Output $verdict
    if ($verifyExit -ne 0) { exit 1 }
    exit 0
} finally {
    $lockStream.Close()
    $lockStream.Dispose()
}
