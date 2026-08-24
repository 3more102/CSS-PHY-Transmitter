# Requirement-to-Evidence Traceability

This matrix separates **source/reference verification**, **RTL implementation**, **RTL execution**, and **target-dependent FPGA evidence**. A missing simulator or FPGA target is never converted into PASS.

| Area | Reference behavior | RTL / artifact | Evidence | Current evidence class |
|---|---|---|---|---|
| PHR | payload length bit 0..6 first, five zeros | `phr_generator.sv` | Python + HDL unit tests | source/reference verified; RTL executed in CI |
| Padding | `N - mod(length,N)`, including full block at exact boundary | `zero_pad_framer.sv` | boundary tests | source/reference verified; RTL executed in CI |
| Payload bit order | byte LSB-first | controller selector | asymmetric patterns 01/80/96/A5/3C | source/reference verified; RTL executed in CI |
| DEMUX | first bit → I, second → Q | `iq_demux.sv` | directed DEMUX + controller checks | source/reference verified; RTL executed in CI |
| 1M mapper | 8 exact 4-chip codewords | `symbol_mapper_1m.sv` | supplied-table equality + exhaustive TB | source/reference + RTL verified |
| 250k mapper | 64 exact 32-chip codewords | `symbol_mapper_250k.sv` | supplied-table equality + exhaustive TB | source/reference + RTL verified |
| 250k interleaver | fixed 64-chip permutation | `bit_interleaver.sv` | permutation impulse test | source/reference + RTL verified |
| Preamble/SFD | 32/80 preamble; rate-specific 16-chip SFD | `preamble_sfd_rom.sv` | full chip stream + unit TB | source/reference + RTL verified |
| QPSK | exact MATLAB four-point orientation | `qpsk_mapper.sv` | exhaustive four combinations | source/reference + RTL verified |
| DQPSK | `S[n]=X[n]S[n-4]`, initial fixed path `1+j` | `dqpsk_encoder.sv` | directed vectors + full integer pipeline | source/reference + RTL verified |
| Chirp ROM | 4 chirps × 152 active samples | `chirp_rom.sv`, generated `.mem` | all four equations; m=1 exact supplied vector | numerical/ROM + RTL verified |
| CSK | four DQPSK symbols × four subchirps + gap | `csk_modulator.sv` | two-group TB + full-chain reference | reference + RTL verified |
| gaps | 10/70, 20/60, 30/50, 40/40 | `csk_modulator.sv` | gap-table test | reference + RTL verified |
| fixed point | signed 6-bit `floor` chirp quantization | six-bit ROMs | exact supplied m=1 vector | verified |
| MSE | normalized threshold < 0.005 | MSE script | 0.000891330083552 at 6-bit floor | verified |
| 1 Mbps | complete packet path | `DATA_RATE=0` | payload matrix 0/1/3/25/127 + protocol TB | GitHub Actions RTL PASS |
| 250 kbps | complete packet path | `DATA_RATE=1` | payload matrix 0/1/3/25/127 + protocol TB | GitHub Actions RTL PASS |
| reset/start rules | one active packet, synchronous reset | top/controller | protocol TB + mid-stream reset sweep (6 depths, sample-exact restart) | protocol PASS both rates; sweep enforced by CI gate |
| done_Tx | after source + CSK queue drain | top | top-level scoreboard | matrix PASS both rates |
| multi-packet | no state leaks between packets | top/controller/DQPSK/CSK | back-to-back TB: 25 -> 25 (distinct contents) -> 127 bytes | executed locally (Icarus-compatible + ModelSim); enforced by CI gate |
| chirp selection | CHIRP_INDEX 1..4 end to end | `chirp_rom.sv` + gap table | full-chain sweep chirps 2/3/4 vs reference model, both rates | executed locally; enforced by CI gate |
| sample clocking | SAMPLE_DIV stretches timing only | top-level divider | divider 2 and 5 value-identical to golden streams | executed locally; enforced by CI gate |
| open-source HDL regression | compile + simulate all TBs | `run_rtl_tests.sh` | Icarus logs + CI evidence gate | PASS; unit markers, full rate/payload matrix, sweeps enforced |
| lint | width/signedness/static RTL quality | `run_lint.sh` | strict Verilator `-Wall` log | PASS; warnings are fatal and clean run emits no diagnostics |
| synthesis | real FPGA netlist | Vivado Tcl | utilization + synthesis log | blocked until exact target/tool exists |
| timing | constrained post-route timing | Vivado implementation flow | clocks + WNS/TNS + route reports | blocked until exact target/tool exists |
| bitstream/board | physical target behavior | board-specific constraints | bitstream + hardware capture | blocked until board/pins/hardware exist |

## Reproducible evidence chain

```text
minimal supplied numerical vectors
        ↓
Python mathematical/bit-accurate reconstruction
        ↓
ROM/vector generation + MSE
        ↓
46 tool-independent tests
        ↓
Icarus SystemVerilog unit/integration regression
        ↓
strict warning-fatal Verilator -Wall lint
        ↓
CI evidence-integrity gate
        ↓
Vivado synthesis/implementation (only with explicit target)
        ↓
board-specific proof
```
