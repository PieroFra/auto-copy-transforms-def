param(
    [string]$Blender = 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe',
    [string]$Suites
)

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$log = Join-Path $PSScriptRoot 'test_out.txt'
$allSuites = @(
    @{ Name = 'test_mod1.py'; Expected = 40 },
    @{ Name = 'test_mod2.py'; Expected = 18 },
    @{ Name = 'test_mod3.py'; Expected = 24 },
    @{ Name = 'test_mod4.py'; Expected = 43 },
    @{ Name = 'test_func1.py'; Expected = 5 },
    @{ Name = 'test_actd.py'; Expected = 106 },
    @{ Name = 'test_mod_types.py'; Expected = 49 },
    @{ Name = 'test_mod_autoprefix.py'; Expected = 35 },
    @{ Name = 'test_mod_learn.py'; Expected = 40 },
    @{ Name = 'test_mod6.py'; Expected = 114 },
    @{ Name = 'test_i18n.py'; Expected = 65 }
)
# Totale atteso delle 11 suite: 539 controlli.
$expectedTotalAll = 0
foreach ($suite in $allSuites) { $expectedTotalAll += $suite.Expected }
$validateAll = -not $PSBoundParameters.ContainsKey('Suites')
$selectedSuites = @()
$suiteAliases = @{}
foreach ($suite in $allSuites) {
    $suiteAliases[$suite.Name] = $suite.Name
    if ($suite.Name -match '^test_(.+)\.py$') { $suiteAliases[$Matches[1]] = $suite.Name }
}
$suiteAliases['types'] = 'test_mod_types.py'
$suiteAliases['autoprefix'] = 'test_mod_autoprefix.py'
$suiteAliases['learn'] = 'test_mod_learn.py'
if ($validateAll) {
    $selectedSuites = $allSuites
} else {
    foreach ($name in ($Suites -split ',')) {
        $name = $name.Trim()
        if (-not $name -or -not $suiteAliases.ContainsKey($name)) {
            throw "Suite sconosciuta o vuota: '$name'"
        }
        $suiteName = $suiteAliases[$name]
        if (-not ($selectedSuites | Where-Object { $_.Name -eq $suiteName })) {
            $selectedSuites += $allSuites | Where-Object { $_.Name -eq $suiteName }
        }
    }
}
$results = @()
$stopAfterSuite = $false

if (-not (Test-Path -LiteralPath $Blender -PathType Leaf)) {
    throw "Eseguibile Blender non trovato: $Blender"
}

Push-Location $root
try {
    foreach ($suite in $selectedSuites) {
        if ($stopAfterSuite) { break }

        $suitePath = Join-Path $PSScriptRoot $suite.Name
        if (-not (Test-Path -LiteralPath $suitePath -PathType Leaf)) {
            $results += [pscustomobject]@{
                Suite = $suite.Name; Attesi = $suite.Expected
                Passati = 'n/d'; Falliti = 'n/d'; Esito = 'FILE ASSENTE'
            }
            continue
        }

        Set-Content -LiteralPath $log -Value '' -Encoding UTF8
        $stdoutPath = Join-Path ([IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString() + '.stdout')
        $stderrPath = Join-Path ([IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString() + '.stderr')
        try {
            $pythonArgument = '"{0}"' -f $suitePath
            $process = Start-Process -FilePath $Blender -ArgumentList @(
                '--background', '--factory-startup', '--python', $pythonArgument
            ) -Wait -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
            $processExit = $process.ExitCode
            $stdout = if (Test-Path -LiteralPath $stdoutPath) { [IO.File]::ReadAllText($stdoutPath) } else { '' }
            $stderr = if (Test-Path -LiteralPath $stderrPath) { [IO.File]::ReadAllText($stderrPath) } else { '' }
            [IO.File]::WriteAllText($log, $stdout + [Environment]::NewLine + $stderr, [Text.Encoding]::UTF8)
        } finally {
            Remove-Item -LiteralPath $stdoutPath, $stderrPath -Force -ErrorAction SilentlyContinue
        }
        if (-not (Test-Path -LiteralPath $log -PathType Leaf)) {
            $results += [pscustomobject]@{
                Suite = $suite.Name; Attesi = $suite.Expected
                Passati = 'n/d'; Falliti = 'n/d'; Esito = 'LOG ASSENTE'
            }
            continue
        }

        $output = Get-Content -LiteralPath $log -Raw
        if ([string]::IsNullOrWhiteSpace($output)) {
            $results += [pscustomobject]@{
                Suite = $suite.Name; Attesi = $suite.Expected
                Passati = 'n/d'; Falliti = 'n/d'; Esito = 'LOG VUOTO'
            }
            continue
        }

        if ($output -match '(?m)\b(SyntaxError|ImportError)\b') {
            $results += [pscustomobject]@{
                Suite = $suite.Name; Attesi = $suite.Expected
                Passati = 'n/d'; Falliti = 'n/d'; Esito = "ERRORE $($Matches[1])"
            }
            $stopAfterSuite = $true
            continue
        }

        $passed = $null
        $failed = $null
        $validSummary = $false
        $modularPassed = [regex]::Matches($output, '(?mi)^Passati:\s*(\d+)\s*$')
        $modularFailed = [regex]::Matches($output, '(?mi)^Falliti:\s*(\d+)\s*$')
        $legacySummary = [regex]::Matches($output, '(?mi)^Superati:\s*(\d+)\s*/\s*(\d+)\s*$')

        if ($modularPassed.Count -gt 0 -and $modularFailed.Count -gt 0) {
            $passed = [int]$modularPassed[$modularPassed.Count - 1].Groups[1].Value
            $failed = [int]$modularFailed[$modularFailed.Count - 1].Groups[1].Value
            $validSummary = $output -match '(?m)^RISULTATO:\s*SUPERATO\s*$'
        } elseif ($legacySummary.Count -gt 0) {
            $summary = $legacySummary[$legacySummary.Count - 1]
            $passed = [int]$summary.Groups[1].Value
            $total = [int]$summary.Groups[2].Value
            $failed = $total - $passed
            $validSummary = $output -match '(?m)^TUTTI I TEST SUPERATI\s*$'
        }

        $expectedTotal = if ($null -ne $passed -and $null -ne $failed) {
            $passed + $failed
        } else { -1 }
        $success = $processExit -eq 0 -and $validSummary -and
            $passed -eq $suite.Expected -and $failed -eq 0 -and
            $expectedTotal -eq $suite.Expected
        $results += [pscustomobject]@{
            Suite = $suite.Name; Attesi = $suite.Expected
            Passati = $(if ($null -eq $passed) { 'n/d' } else { $passed })
            Falliti = $(if ($null -eq $failed) { 'n/d' } else { $failed })
            Esito = $(if ($success) { 'SUPERATO' } else { 'DIVERGENZA' })
        }
    }
} finally {
    Pop-Location
}

$results | Format-Table -AutoSize | Out-Host
$totalPassed = 0
foreach ($result in $results) {
    if ($result.Passati -match '^\d+$') { $totalPassed += [int]$result.Passati }
}
$allTotalValid = -not $validateAll -or ($results.Count -eq $allSuites.Count -and $totalPassed -eq $expectedTotalAll)
if ($stopAfterSuite -or $results.Count -ne $selectedSuites.Count -or -not $allTotalValid -or
    @($results | Where-Object { $_.Esito -ne 'SUPERATO' }).Count -gt 0) {
    exit 1
}
exit 0
