# Test Matrix - CSS PHY Transmitter RTL

All counts below were re-executed in THIS release worktree
(`closure/css-release-evidence` @ 20ca9fa + release commits), 2026-08-24.
Nothing is inferred from old reports.

| ID | Test / script | Class | What it proves | Result (this session) |
|----|---------------|-------|----------------|----------------------|
| T1 | `tb/tb_css_tx_top.v` via `scripts/run_regression.ps1` | FULL-CHAIN | RTL sample stream == Python golden model (bit-exact vs MATLAB fixed point) for 8 official cases; exact equality, 0 mismatches | **8/8 PASS** |
| T2 | same TB, vectors from `scripts/gen_edge_vectors.py` (`run_regression.ps1 -Vectors sim_edge`) | FULL-CHAIN (edge) | plen = 0, 1, 3, 20/25 crossover, 127 at both rates incl. PHR/padding/sample-count exactness | **10/10 PASS** |
| T3 | `tb/tb_cw_rom_serialize.v` + `scripts/check_cw_serialization.py` | UNIT (exhaustive) | serialized chip order of codeword ROM == MATLAB tables: all 8 symbols @1 Mb/s + all 64 reachable symbols @250 kb/s | **72/72 PASS, 0 failures** |
| T4 | `scripts/check_interleaver.py` | STATIC / REFERENCE-CONSISTENCY | perm() == MATLAB `bitInterleaver` output_indices; group order G0 G13 G2 G15 G4 G9 G6 G11 G8 G5 G10 G7 G12 G1 G14 G3 | **PASS** |
| T5 | `scripts/test_vector_consistency.py` | REFERENCE-CONSISTENCY | every committed vector regenerates byte-for-byte; stimulus/golden seed+CRC consistency per case (anti seed-drift guard) | **PASS (0 failures)** |
| T6 | `scripts/compute_mse.py` | REFERENCE-CONSISTENCY (accuracy) | floating vs fixed-point MSE per assignment Section 3.3 | **PASS, MSE = 8.913e-04 < 0.005** |
| T7 | `tb/tb_control_restart.v` | INTEGRATION (control) | reset, start, done/busy-fall, back-to-back second packet, rate change between packets, mid-packet reset recovery | **FAIL -> Defect D-1** (busy never deasserts; datapath phases verified bit-exact before stall). See reports/DEFECT_REPORT.md |
| T8 | ModelSim compile of production RTL only (`vlog`, fresh work) | STATIC (compile/lint) | production RTL compiles standalone | **0 errors, 0 warnings** |
| T9 | ROM negative tests: hide `chirp_rom.hex` / `cw32.hex` in scratch sim dirs | NEGATIVE TEST | missing ROM fails loudly in simulation | chirp ROM: FATAL fires (pre-existing); codeword ROM: guard was dead (D-2), repaired this session, now FATAL fires; positive case re-verified |

## Coverage notes / gaps

- UNIT testbenches exist for the Symbol Mapper path (T3 covers the mapper
  ROM exhaustively through serialization). The assignment asks for unit
  TBs for Symbol Mapper, DQPSK encoder and CSK generator specifically;
  DQPSK and CSK are currently covered only through full-chain equality
  (any error would break every subchirp) and the stage audits in
  reports/root_cause_codeword_order.md. Dedicated standalone DQPSK/CSK
  unit TBs remain a gap (see DELIVERABLE_CHECKLIST.md).
- No synthesis/timing evidence exists anywhere in the repository.

## Exact commands (tested in this worktree)

```
powershell -ExecutionPolicy Bypass -File scripts\run_regression.ps1
python scripts\gen_edge_vectors.py
powershell -ExecutionPolicy Bypass -File scripts\run_regression.ps1 -Vectors sim_edge
# in a scratch sim dir with vectors copied:
#   vlib work; vlog ..\rtl\*.v ..\tb\tb_css_tx_top.v; vsim -c "run -all; quit -f" ...
python scripts\check_cw_serialization.py sim_unit
python scripts\check_interleaver.py
python scripts\test_vector_consistency.py
python scripts\compute_mse.py
```
