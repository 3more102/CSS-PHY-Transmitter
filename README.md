# CSS PHY Transmitter RTL

FPGA implementation of the IEEE 802.15.4 Chirp Spread Spectrum (CSS) PHY
transmitter (both 1 Mb/s and 250 kb/s data rates), verified bit-exact against
the supplied MATLAB fixed-point reference.

## Status

RTL FUNCTIONALLY VERIFIED (single-packet scope). Synthesis/timing NOT yet
executed. See `reports/FINAL_VERIFICATION.md` and `reports/DEFECT_REPORT.md`.

## Prerequisites

- ModelSim ASE / Intel FPGA Starter Edition 18.1 at
  `C:\intelFPGA\18.1\modelsim_ase` (path used by `scripts\run_regression.ps1`)
- Python 3.x (standard library only)
- Windows PowerShell 5.1

## Repository structure

- `rtl/`          Synthesizable Verilog RTL (`css_tx_top.v` top level)
- `tb/`           Self-checking Verilog testbenches
- `matlab/`       Supplied MATLAB floating/fixed-point reference models
- `vectors/`      Committed golden vectors + ROM tables + manifest
- `scripts/`      Vector generation, regression runners, consistency checks
- `reports/`      Verification, traceability and defect reports
- `docs/`         Reference audit notes
- `reference/`    Project assignment and supplied reference documents

## Reproduce everything from a fresh checkout

```powershell
# 1. Official full-chain regression: regenerates vectors/, compiles RTL+TB,
#    runs all 8 cases under ModelSim. Expect "TOTAL: 8/8 cases passed".
powershell -ExecutionPolicy Bypass -File scripts\run_regression.ps1

# 2. Golden-vector reproducibility / seed-consistency guards.
#    Expect "RESULT: PASS (0 failures)".
python scripts\test_vector_consistency.py

# 3. Edge-case regression (payload lengths 0, 1, 3, 20/25, 127; both rates).
#    Generates sim_edge/ then runs 10 cases. Expect "TOTAL: 10/10".
python scripts\gen_edge_vectors.py
powershell -ExecutionPolicy Bypass -File scripts\run_regression.ps1 -Vectors sim_edge

# 4. Exhaustive codeword serialization check vs MATLAB tables.
#    Run tb_cw_rom_serialize in a scratch dir containing vectors\*.hex:
New-Item -ItemType Directory -Force -Path sim_unit
Copy-Item vectors\*.hex sim_unit\
Push-Location sim_unit
& C:\intelFPGA\18.1\modelsim_ase\win32aloem\vlib.exe work
& C:\intelFPGA\18.1\modelsim_ase\win32aloem\vlog.exe -quiet ..\rtl\css_codeword_rom.v ..\tb\tb_cw_rom_serialize.v
& C:\intelFPGA\18.1\modelsim_ase\win32aloem\vsim.exe -c -quiet -do "run -all; quit -f" work.tb_cw_rom_serialize
Pop-Location
python scripts\check_cw_serialization.py sim_unit   # expect "72 codewords, 0 failures"

# 5. Interleaver static audit vs MATLAB bitInterleaver.
python scripts\check_interleaver.py                # expect PASS / PASS

# 6. MSE accuracy (floating-point vs fixed-point), assignment threshold < 0.005.
python scripts\compute_mse.py                      # expect MSE = 8.913e-04, PASS

# 7. Control/restart coverage (KNOWN FAIL - Defect D-1, see reports/).
#    Verifies reset/start/done semantics, back-to-back packets, mid-packet reset.
```

## Compile RTL only

```powershell
Push-Location <scratch dir with vlib work>
& C:\intelFPGA\18.1\modelsim_ase\win32aloem\vlog.exe ..\rtl\css_chirp_rom.v `
    ..\rtl\css_codeword_rom.v ..\rtl\css_pkt_ctrl.v ..\rtl\css_dqcsk_mod.v `
    ..\rtl\css_tx_top.v
Pop-Location
# current status: 0 errors, 0 warnings
```

## Synthesis / timing

Not available in this environment (Quartus not installed). No synthesis or
timing evidence exists in the repository.

## Expected PASS criteria

| Suite | Criterion |
|---|---|
| Official regression | 8/8 cases, exact sample equality, 0 mismatches |
| Edge regression | 10/10 cases |
| Codeword serialization | 72 checked, 0 failures |
| Interleaver audit | perm == MATLAB output_indices |
| Vector consistency | 0 failures |
| MSE | < 0.005 (measured 8.9e-04) |

## Known tool/environment limitations

- Quartus/Vivado not installed -> no synthesis/utilization/timing evidence.
- Multi-packet operation requires reset between packets until Defect D-1
  (`busy` deassertion) is fixed - see `reports/DEFECT_REPORT.md`.
- ROM tables are loaded via `$readmemh`; simulation must run in a directory
  containing `chirp_rom.hex`, `cw4.hex`, `cw32.hex` (regression scripts copy
  them automatically). Missing ROMs fail loudly with a FATAL message.
