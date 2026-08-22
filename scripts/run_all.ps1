$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
python matlab/vector_generation/generate_vectors.py
python matlab/mse/mse_analysis.py
python -m unittest discover -s tests -p "test_*.py" -v
if (Get-Command iverilog -ErrorAction SilentlyContinue) {
    bash scripts/run_rtl_tests.sh
} else {
    Write-Host "SKIP/BLOCKED: Icarus Verilog is not installed."
}
if (Get-Command verilator -ErrorAction SilentlyContinue) {
    bash scripts/run_lint.sh
} else {
    Write-Host "SKIP/BLOCKED: Verilator is not installed."
}
