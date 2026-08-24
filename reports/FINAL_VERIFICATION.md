# Final Verification Report - CSS PHY Transmitter RTL

Date        : 2026-08-24
Worktree    : C:\Users\omar\CSS_PHY_RTL_release
Branch      : closure/css-release-evidence
Base HEAD   : 20ca9faf443cb31b41124790f099d17dfa51130f
              ("integrate(css-phy): verified fix + regression hardening")

## Reference sources used

- `matlab/original/CSS_PHY_Trasmitter-Floating-Fixed Point/` (supplied MATLAB
  floating + fixed point models, codeword/chirp/payload tables)
- `reference/CSS_PHY_Transmitter_Project.docx` (assignment: interface,
  deliverables, MSE criterion)
- `reference/CSS_PHY_Transmitter-Reference Document.docx` (CSS PHY theory)

## Test environment

- Windows, PowerShell 5.1, Python 3.12.10
- ModelSim ASE 10.5b (Intel FPGA Starter Edition 18.1),
  C:\intelFPGA\18.1\modelsim_ase
- Quartus: NOT INSTALLED on this host

## Results (all re-executed from this clean worktree; see TEST_MATRIX.md)

| Item | Result | Status |
|---|---|---|
| Official full-chain regression | **8/8 PASS**, exact sample-by-sample equality, 0 mismatches (7842 / 16896 / 35328 / 29184 / 62976 / 136704 / 9216 / 47616 samples) | VERIFIED |
| Edge regression (plen 0/1/3/20-25/127, both rates) | **10/10 PASS** (2850..136704 samples) | VERIFIED |
| Codeword serialization exhaustive | **72/72 PASS** (8 symbols @1 Mb/s + 64 @250 kb/s) | VERIFIED |
| Interleaver vs MATLAB bitInterleaver | perm + group order PASS | VERIFIED |
| Golden vector regeneration | byte-for-byte reproducible, per-case seed/CRC consistent (no seed=0 drift) | VERIFIED |
| MATLAB fixed-point comparison | RTL == fixed-point golden exactly (that is the 8/8 above) | VERIFIED |
| MSE (floating vs fixed) | chirp MSE = 8.913e-04 for m=1..4; full-chain output MSE = 8.913e-04 < 0.005 threshold (`scripts/compute_mse.py`) | VERIFIED |
| ModelSim compile of production RTL | 0 errors, 0 warnings (fresh vlib, vlog without -quiet) | VERIFIED |
| ROM dependency negative tests | missing chirp_rom.hex -> FATAL; missing cw32.hex -> FATAL after D-2 guard repair; positive behavior unchanged (regression re-run 8/8) | VERIFIED |
| Control/restart coverage (reset, done, 2nd packet, rate change, mid-packet reset) | FAIL -> **Defect D-1**: busy never deasserts after eop; second packet cannot start. Datapath phases verified bit-exact before the stall. NOT patched in this session. | BLOCKED (defect open) |
| Synthesis | no tool, no evidence in any branch/worktree | NOT YET EXECUTED |
| Timing / Fmax | none | NOT YET EXECUTED |
| On-board demo | none | NOT YET EXECUTED |

## Root causes preserved in final evidence

1. Codeword bit order (reports/root_cause_codeword_order.md): codewords were
   stored c0-at-MSB while the serializer emitted LSB-first, reversing every
   non-palindromic codeword. Escaped early testing because codewords 0-3 are
   palindromic; first verified divergence at data codeword #4, chip 64,
   global bit address 24. Fix: storage and serializer aligned to MATLAB
   c0-first ordering. QPSK/DQPSK/CSK were never the root cause.
2. Golden-seed drift (same report): golden generator used seed=0 while DUT
   stimulus used seed=case_id, so 7/8 vectors encoded a different payload.
   Fix: case seed propagated consistently; permanent guards now in
   gen_golden_vectors.py + test_vector_consistency.py (re-proven this session).

## Fixed-point rule (audited against MATLAB source)

`runMe.m`: `chirpSequence_Tx = floor(chirpSequence * (2^(TxDACbitNumber-1)-1))`
with TxDACbitNumber = 6 -> floor(x*31), applied to chirp ROM contents only;
all other blocks integer-exact. RTL-vs-MATLAB standard is EXACT equality;
floating-vs-fixed standard is the MSE bound. Not mixed anywhere.

## Known limitations / open items

- D-1 (open RTL defect): done/busy deassertion - multi-packet operation
  requires reset between packets until fixed.
- No standalone DQPSK / CSK unit testbenches (covered via full chain).
- No synthesis, timing, or board demonstration evidence.
- Assignment interface deviations documented in TOP_LEVEL_INTERFACE.md.

## Release readiness determination

**A. RTL FUNCTIONALLY VERIFIED** for single-packet transmission at both
data rates and all payload lengths 0..127 (bit-exact vs the supplied
MATLAB fixed-point reference), with accuracy within the required MSE bound.
NOT B or C: synthesis/timing unavailable and unexecuted; multi-packet
control blocked by D-1.
