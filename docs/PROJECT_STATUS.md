# Project Status

Status vocabulary: **NOT STARTED / IN PROGRESS / BLOCKED / IMPLEMENTED / VERIFIED**.

## Evidence command

```bash
make verify
```

The driver regenerates deterministic vectors/ROMs, recalculates MSE, executes tool-independent tests, detects external tools, and writes `reports/verification_summary.{txt,json}`. Missing tools are never converted into PASS.

## Established source/reference evidence

| Item | Status |
|---|---|
| 1 Mbps codeword table | VERIFIED |
| 250 kbps codeword table | VERIFIED |
| supplied m=1 chirp vectors | VERIFIED, exact 152 real + 152 imag |
| chirp m=1..4 generated ROMs | VERIFIED against reference equations |
| bit-order audit | VERIFIED |
| required payload matrix | VERIFIED at reference/architecture level |
| all payload lengths group alignment | VERIFIED for 0..127 |
| deterministic randomized equivalence | VERIFIED, seed `0x802154` |
| six-bit floor MSE | VERIFIED: `0.000891330083552 < 0.005` |
| native MATLAB execution | environment-dependent / not claimed |

The pre-publication tool-independent suite executed **46 Python tests with 0 failures**.

## RTL

All required transmitter blocks and top-level integration are implemented. Self-checking SystemVerilog tests cover payload RAM, PHR, padding, DEMUX, preamble/SFD, both symbol mappers, interleaver, QPSK, DQPSK, chirp ROM, CSK, controller, protocol behavior, and top-level samples.

RTL is marked **IMPLEMENTED** until an HDL simulator actually executes the tests. GitHub Actions provisions Icarus Verilog and Verilator and runs the same evidence driver.

## FPGA / timing

The Vivado flow and timing parser are implemented, but real synthesis/place-route/timing remain **BLOCKED** until Vivado and an exact FPGA part/clock target are supplied. No target-dependent metric is estimated.
