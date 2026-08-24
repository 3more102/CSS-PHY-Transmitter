# run_regression.ps1 - compile RTL + TB and run the full golden-vector
# regression under ModelSim (Intel FPGA Starter Edition).
#
# Usage: powershell -File scripts\run_regression.ps1 [-Cases tag1,tag2]
[CmdletBinding()]
param(
    [string[]]$Cases = @()
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot   # repo root
$sim  = Join-Path $root "sim"
$vec  = Join-Path $root "vectors"
$modelsim = "C:\intelFPGA\18.1\modelsim_ase\win32aloem"

if (-not (Test-Path $modelsim)) {
    Write-Error "ModelSim not found at $modelsim"
}

Write-Host "=== [1/4] generating golden vectors ==="
& python (Join-Path $root "scripts\gen_golden_vectors.py")
if ($LASTEXITCODE -ne 0) { Write-Error "golden vector generation failed" }

Write-Host "=== [2/4] preparing sim workspace ==="
New-Item -ItemType Directory -Force -Path $sim | Out-Null
Copy-Item (Join-Path $vec "*.hex") $sim -Force

Push-Location $sim
try {
    if (Test-Path work) { Remove-Item -Recurse -Force work }
    & "$modelsim\vlib.exe" work | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Error "vlib failed" }

    Write-Host "=== [3/4] compiling RTL + testbench ==="
    & "$modelsim\vlog.exe" -quiet ..\rtl\css_chirp_rom.v ..\rtl\css_codeword_rom.v `
        ..\rtl\css_pkt_ctrl.v ..\rtl\css_dqcsk_mod.v ..\rtl\css_tx_top.v `
        ..\tb\tb_css_tx_top.v 2>&1 | Tee-Object -Variable vlogOut
    if ($LASTEXITCODE -ne 0) { Write-Error "vlog failed" }

    Write-Host "=== [4/4] running regression cases ==="
    # manifest columns: tag rate plen m nsamp case_id payload_crc
    $rows = @(Get-Content (Join-Path $vec "manifest.txt") |
        ForEach-Object { ($_ -split '\s+') | Where-Object { $_ } })
    if (($rows.Count % 7) -ne 0) { Write-Error "unexpected manifest column count" }
    $results = @()
    for ($ln = 0; $ln -lt $rows.Count; $ln += 7) {
        $tag   = $rows[$ln]
        $rate  = $rows[$ln + 1]
        $plen  = $rows[$ln + 2]
        $m     = $rows[$ln + 3]
        $nsamp = $rows[$ln + 4]
        if ($Cases.Count -gt 0 -and $Cases -notcontains $tag) { continue }

        $log = "run_$tag.log"
        & "$modelsim\vsim.exe" -c -quiet -do "run -all; quit -f" `
            work.tb_css_tx_top `
            "+rate=$rate" "+plen=$plen" "+m=$m" "+nsamp=$nsamp" `
            "+payload=payload_$tag.hex" "+golden=golden_$tag.hex" `
            2>&1 | Out-File $log -Encoding ascii

        $pass = Select-String -Path $log -Pattern "TB RESULT: PASS" -Quiet
        $fatal = Select-String -Path $log -Pattern "FATAL|TB ERROR" |
            Select-Object -First 3 -ExpandProperty Line
        $status = "PASS"; if (-not $pass) { $status = "FAIL" }
        Write-Host ("{0,-20} {1} ({2} samples)" -f $tag, $status, $nsamp)
        if ($fatal) { $fatal | ForEach-Object { Write-Host "    $_" } }
        $results += [pscustomobject]@{ Case = $tag; Status = $status; Samples = $nsamp }
    }

    # summary report
    $reportPath = Join-Path $root "reports\regression_report.txt"
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $lines = @(
        "============================================================",
        "CSS PHY TRANSMITTER REGRESSION REPORT",
        "Generated : $stamp",
        "Simulator : ModelSim ASE 18.1",
        "------------------------------------------------------------")
    foreach ($r in $results) {
        $lines += ("{0,-20} {1,-5} {2,8} samples" -f $r.Case, $r.Status, $r.Samples)
    }
    $npass = ($results | Where-Object Status -eq "PASS").Count
    $lines += "------------------------------------------------------------"
    $lines += ("TOTAL: {0}/{1} cases passed" -f $npass, $results.Count)
    $lines += "============================================================"
    New-Item -ItemType Directory -Force -Path (Join-Path $root "reports") | Out-Null
    Set-Content -Path $reportPath -Value $lines -Encoding ascii
    Write-Host $lines[-2]

    Pop-Location
    if ($npass -ne $results.Count) { exit 1 } else { exit 0 }
} finally {
    Pop-Location
}
