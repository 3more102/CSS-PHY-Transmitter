# Requirements and Source Hierarchy

## Authoritative source priority

The project was developed from supplied course material using this hierarchy:

1. **Assignment document** — external interface, required blocks, deliverables, verification, MSE and FPGA-flow expectations.
2. **Supplied MATLAB fixed-point implementation** — numerical behavior, bit/data ordering, quantization, truncation/rounding semantics and expected samples.
3. **Supplied floating-point MATLAB model** — mathematical waveform reference and fixed-point accuracy comparison.
4. **CSS reference document** — PPDU structure, coding, interleaver, QPSK/DQPSK, chirp generation, timing and historical hardware architecture.

The original PDF/DOCX/ZIP course materials are not republished in this public repository. Minimal numerical vectors required to reproduce source-equivalence tests are retained under `matlab/original/`.

## Mandatory functional requirements

| Requirement | Implemented location | Verification path |
|---|---|---|
| PSDU 0..127 bytes | `payload_ram.sv`, controller | Python exhaustive length grouping + RTL matrix |
| required `clk/reset/start_Tx/payloadLength/done_Tx/Tx_real/Tx_imag` | `css_phy_tx_top.sv` | static interface test |
| explicit payload loading | `payload_wr_en`, `payload_addr`, `payload_din` | payload RAM + integration TB |
| 1 Mbps + 250 kbps | `DATA_RATE` parameter | reference + RTL matrix |
| 12-bit PHR | `phr_generator.sv` | directed PHR tests |
| MATLAB-exact padding | `zero_pad_framer.sv` | boundary tests including full-block case |
| first serial bit to I, second to Q | `iq_demux.sv` + controller | directed anti-reversal tests |
| 1 Mbps 3→4 mapping | `symbol_mapper_1m.sv` | exhaustive 8-symbol test |
| 250 kbps 6→32 mapping | `symbol_mapper_250k.sv` | exhaustive 64-symbol test |
| 250 kbps interleaver | `bit_interleaver.sv` | 64-position permutation test |
| preamble + rate-specific SFD | `preamble_sfd_rom.sv` | unit + controller stream tests |
| QPSK map | `qpsk_mapper.sv` | exhaustive four-point test |
| four-symbol DQPSK feedback | `dqpsk_encoder.sv` | directed unit + full chain |
| four chirp sequences | `chirp_rom.sv`, `rtl/rom/` | ROM/equation comparison |
| 38 samples/subchirp, 152 active samples | `chirp_rom.sv`, `csk_modulator.sv` | exact m=1 vector + CSK tests |
| even/odd chirp gaps | `csk_modulator.sv` | gap-table/full stream tests |
| signed 8-bit I/Q outputs | `css_phy_tx_top.sv` | architecture range tests |
| normalized MSE < 0.005 | `matlab/mse/mse_analysis.py` | measured 6-bit floor MSE 0.000891330083552 |
| unit + integration verification | `tb/`, `tests/` | `make verify`, `make rtl` |
| synthesis/timing preparation | Vivado Tcl + XDC | target-dependent; no fabricated results |

## Deliberate interface extension

The assignment requires payload data to be loaded before transmission but does not fully define the write protocol naming. The design therefore adds only:

- `payload_wr_en`
- `payload_addr[6:0]`
- `payload_din[7:0]`

The mandatory external signals remain unchanged.
