# Integration Report - verified fix d416ea8

Integration branch : integration/verified-fix (worktree CSS_PHY_RTL_integrate)
Cherry-pick        : d416ea8 -> 3069a98, applied CLEANLY onto master (2efd326)
Primary untracked work: preserved untouched (pre-fix rtl/, tb/, sim/ left as-is)

## Post-integration verification

Official full-chain regression (scripts/run_regression.ps1, regenerated vectors):
  rate0_len20_m1  PASS  7842      rate1_len20_m1  PASS  29184
  rate0_len55_m1  PASS  16896     rate1_len55_m1  PASS  62976
  rate0_len127_m1 PASS  35328     rate1_len127_m1 PASS 136704
  rate0_len25_m2  PASS  9216      rate1_len40_m4  PASS  47616
  TOTAL 8/8, exact sample-by-sample equality, 0 mismatches.

Edge-case regression (both rates, plen = 0, 1, 3, 20/25, 127):
  edge_rate0_len0 2850 PASS   edge_rate1_len0  7680 PASS
  edge_rate0_len1 3072 PASS   edge_rate1_len1  7680 PASS
  edge_rate0_len3 3618 PASS   edge_rate1_len3 10752 PASS
  edge_rate0_len20 7842 PASS  edge_rate1_len25 32256 PASS
  edge_rate0_len127 35328 PASS edge_rate1_len127 136704 PASS
  PHR/padding/sample-count/Tx_real/Tx_imag all exact vs MATLAB fixed point.

Codeword ROM exhaustive unit test (tb_cw_rom_serialize + check_cw_serialization.py):
  1 Mbps  : 8/8 symbols, serialized chip order == codeword_1Mbs table (c0 first)
  250kbps : 64/64 reachable symbols, serialized order == codeword_250kbs table
  Verifies actual serializer output sequence, not stored register values.

Interleaver static audit (check_interleaver.py):
  perm() == MATLAB bitInterleaver output_indices : PASS
  output group order G0 G13 G2 G15 G4 G9 G6 G11 G8 G5 G10 G7 G12 G1 G14 G3 : PASS
  No ordering workaround remains after the comb fix.

QPSK / DQPSK / CSK:
  Re-verified through the full-chain vectors above; no downstream changes made.

Golden generator seed-drift protection:
  - gen_golden_vectors.py now asserts stimulus bytes == golden payload bytes,
    asserts a different case_id changes the chip stream, prints per-case
    case_id/seed/rate/plen/payload_crc, and writes them into manifest.txt.
  - scripts/test_vector_consistency.py permanently re-verifies that every
    committed golden file regenerates byte-for-byte from the committed
    payload stimulus and manifest metadata.  RESULT: PASS (0 failures).

Synthesis safety:
  ModelSim compile of production RTL only: 0 errors, 0 warnings.
  All $display sites (3) are inside `synthesis translate_off/on` guards.
  ROM init via initial/$readmemh + constant-bound loops: standard FPGA flow.
  No latches, no width/sign changes from the fix (pure table-order/wiring).
  Quartus not installed on this host; elaboration-level lint only.

Harness hardening added during integration:
  css_chirp_rom.v / css_codeword_rom.v now emit a FATAL simulation message if
  their .hex files are missing (guarded translate_off).  During integration a
  missing cw32.hex in a scratch sim directory silently corrupted 250 kb/s
  output (step_of(X) hits the case default); this guard prevents recurrence.
  Verified: FATAL fires when hex absent; full regression unaffected otherwise.

Debug artifacts removed/excluded:
  Primary tree scratch dir sim_verify/ (incl. instrumented copies) deleted.
  Integration worktree build dirs (sim/, sim_unit/, sim_edge/, sim_dbg2/,
  sim_guard/) are untracked scratch and removed before commit.
  Production RTL contains no debug instrumentation beyond guarded guards.
