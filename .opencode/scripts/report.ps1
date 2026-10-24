# report.ps1 — riepilogo della telemetria delle verifiche.
#
# Legge .opencode\metrics.jsonl e dice, per agente, quante verifiche sono
# passate, quante sono fallite e quanto tempo hanno richiesto. Dopo una
# ventina di task i numeri dicono quale agente sbaglia davvero.
#
# Uso:
#   powershell -NoProfile -ExecutionPolicy Bypass -File .opencode\scripts\report.ps1
#   ... -Last 20
param(
    [int]$Last = 0,
    [string]$Root = ""
)

$ErrorActionPreference = "Stop"
if (-not $Root) { $Root = (Get-Item "$PSScriptRoot\..\..").FullName }
$metrics = Join-Path $Root ".opencode\metrics.jsonl"

if (-not (Test-Path -LiteralPath $metrics)) {
    Write-Output "REPORT | nessuna telemetria: $metrics"
    exit 0
}

$rows = @()
foreach ($line in (Get-Content -LiteralPath $metrics)) {
    $t = $line.Trim()
    if (-not $t) { continue }
    try { $rows += ($t | ConvertFrom-Json) } catch { }
}
if ($rows.Count -eq 0) {
    Write-Output "REPORT | telemetria vuota"
    exit 0
}
if ($Last -gt 0 -and $rows.Count -gt $Last) { $rows = $rows | Select-Object -Last $Last }

Write-Output ("REPORT | run totali={0} | finestra='{1}'" -f $rows.Count, $(if ($Last -gt 0) { "ultimi $Last" } else { "tutte" }))

Write-Output ""
Write-Output "Per agente:"
$rows | Group-Object agent | ForEach-Object {
    $g = $_.Group
    $ok = @($g | Where-Object { $_.status -eq "OK" }).Count
    $ko = @($g | Where-Object { $_.status -ne "OK" }).Count
    $avg = ($g | Measure-Object -Property duration_s -Average).Average
    $name = if ($_.Name) { $_.Name } else { "(senza agent)" }
    "  {0,-14} ok={1,-4} fail={2,-4} media={3,5:N1}s" -f $name, $ok, $ko, $avg
}

Write-Output ""
Write-Output "Per esito:"
$rows | Group-Object status | ForEach-Object {
    "  {0,-6} {1}" -f $_.Name, $_.Count
}

$failRows = @($rows | Where-Object { $_.status -ne "OK" })
if ($failRows.Count -gt 0) {
    Write-Output ""
    Write-Output "Fallimenti recenti:"
    $failRows | Select-Object -Last 5 | ForEach-Object {
        "  {0} | agent={1} | task={2} | reason={3} | passed={4} failed={5}" -f `
            $_.ts, $(if ($_.agent) { $_.agent } else { "-" }), $_.task, $_.reason, $_.passed, $_.failed
    }
}

$avgAll = ($rows | Measure-Object -Property duration_s -Average).Average
$maxAll = ($rows | Measure-Object -Property duration_s -Maximum).Maximum
Write-Output ""
Write-Output ("Durata: media={0:N1}s max={1:N1}s" -f $avgAll, $maxAll)
