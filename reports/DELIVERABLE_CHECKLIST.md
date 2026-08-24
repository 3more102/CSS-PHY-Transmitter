# Assignment Deliverable Checklist

Authority: `reference/CSS_PHY_Transmitter_Project.docx` (Sections 5-9).

| # | Required deliverable | Status | Evidence |
|---|---------------------|--------|----------|
| 1 | Modular RTL, one module per block (Sec 5.1) | PASS | `rtl/css_pkt_ctrl.v` (framing/padding/demux/mapper/interleaver/controller), `css_codeword_rom.v` (symbol mapper ROMs), `css_dqcsk_mod.v` (QPSK+DQPSK+CSK modulator), `css_chirp_rom.v` (chirp ROM), `css_tx_top.v`. Note: demux/mapper/interleaver are sub-blocks inside pkt_ctrl rather than separate modules; functionally complete, modularity partially consolidated. |
| 2 | Top-level interface per Section 5 table | PARTIAL | Functionally equivalent; deviations documented in reports/TOP_LEVEL_INTERFACE.md (async rst_n vs sync reset, 7-bit length/data width, done_Tx defect D-1). |
| 3 | Unit TB: Symbol Mapper vs MATLAB values | PASS | tb_cw_rom_serialize + check_cw_serialization.py, exhaustive 72/72 vs codeword tables. |
| 4 | Unit TB: DQPSK encoder vs MATLAB values | MISSING (coverage via full chain) | No standalone DQPSK unit TB. Covered bit-exactly by full-chain vectors + stage audit (root_cause report). |
| 5 | Unit TB: CSK generator vs MATLAB values | MISSING (coverage via full chain) | No standalone CSK unit TB. Chirp ROM contents byte-reproducible from MATLAB dumps; modulation covered by full chain. |
| 6 | Integration full-chain TB vs fixed-point MATLAB, >=3 lengths incl. 0/1 and 127 | PASS | tb_css_tx_top: 8 official cases + 10 edge cases = 18 cases, both rates, plen 0..127, exact equality. |
| 7 | MSE accuracy report (< 0.005 floating vs fixed) | PASS | scripts/compute_mse.py: chirp-sequence MSE 8.913e-04 for all m=1..4; full-chain output MSE identical bound. Threshold 0.005 (IEEE 802.15.4 6.5a.5.1). |
| 8 | Behavioral simulation logs/waveforms | PARTIAL | Text logs (reports/regression_report.txt generated; run_*.log in sim/). No waveform screenshots committed (VCD dump supported via +vcd). |
| 9 | Synthesis for target FPGA + utilization | BLOCKED | Quartus/Vivado not available on this host; no synthesis evidence on any branch/worktree. |
| 10 | Implementation + timing summary / Fmax | BLOCKED | Same as #9. |
| 11 | Written project report (block diagram, FSM, word-length/MSE justification, verification results) | PARTIAL | reports/ now contain traceability, interface, test matrix, root causes, final verification. Still missing: block diagram & FSM diagrams as figures, board demo. |
| 12 | On-board demonstration (device programming) | NOT YET EXECUTED | Requires synthesis toolchain + FPGA board. |

## Release status implied by this checklist

RTL FUNCTIONALLY VERIFIED (single-packet scope; multi-packet control
blocked by Defect D-1). SYNTHESIS AND TIMING PENDING.
