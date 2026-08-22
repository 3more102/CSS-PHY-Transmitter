# Requirement-to-Evidence Traceability

This matrix separates **source/reference verification**, **RTL implementation**, **RTL execution**, and **target-dependent FPGA evidence**. A missing simulator or FPGA target is never converted into PASS.

| Area | Reference behavior | RTL / artifact | Evidence | Current evidence class |
|---|---|---|---|---|
| PHR | payload length bit 0..6 first, five zeros | `phr_generator.sv` | Python + HDL unit tests | source/reference verified; RTL implemented |
| Padding | `N - mod(length,N)`, including full block at exact boundary | `zero_pad_framer.sv` | boundary tests | source/reference verified; RTL implemented |
| Payload bit order | byte LSB-first | controller selector | asymmetric patterns 01/80/96/A5/3C | source/reference verified |
| DEMUX | first bit → I, second → Q | `iq_demux.sv` | directed DEMUX + controller checks | source/reference verified; RTL implemented |
| 1M mapper | 8 exact 4-chip codewords | `symbol_mapper_1m.sv` | supplied-table equality + exhaustive TB | source/reference verified |
| 250k mapper | 64 exact 32-chip codewords | `symbol_mapper_250k.sv` | supplied-table equality + exhaustive TB | source/reference verified |
| 250k interleaver | fixed 64-chip permutation | `bit_interleaver.sv` | permutation impulse test | source/reference verified |
| Preamble/SFD | 32/80 preamble; rate-specific 16-chip SFD | `preamble_sfd_rom.sv` | full chip stream + unit TB | source/reference verified |
| QPSK | exact MATLAB four-point orientation | `qpsk_mapper.sv` | exhaustive four combinations | source/reference verified |
| DQPSK | `S[n]=X[n]S[n-4]`, initial fixed path `1+j` | `dqpsk_encoder.sv` | directed vectors + full integer pipeline | source/reference verified |
| Chirp ROM | 4 chirps × 152 active samples | `chirp_rom.sv`, generated `.mem` | all four equations; m=1 exact supplied vector | verified at numerical/ROM level |
| CSK | four DQPSK symbols × four subchirps + gap | `csk_modulator.sv` | two-group TB + full-chain reference | reference verified; RTL implemented |
| gaps | 10/70, 20/60, 30/50, 40/40 | `csk_modulator.sv` | gap-table test | reference verified |
| fixed point | signed 6-bit `floor` chirp quantization | six-bit ROMs | exact supplied m=1 vector | verified |
| MSE | normalized threshold < 0.005 | MSE script | 0.000891330083552 at 6-bit floor | verified |
| 1 Mbps | complete packet path | `DATA_RATE=0` | required payload matrix + randomized reference checks | reference/architecture verified |
| 250 kbps | complete packet path | `DATA_RATE=1` | required payload matrix + randomized reference checks | reference/architecture verified |
| reset/start rules | one active packet, synchronous reset | top/controller | protocol TB | RTL test prepared; simulator result depends on actual run |
| done_Tx | after source + CSK queue drain | top | top-level scoreboard | RTL test prepared |
| open-source HDL regression | compile + simulate all TBs | `run_rtl_tests.sh` | Icarus logs | actual CI/local result required |
| lint | width/signedness/static RTL quality | `run_lint.sh` | Verilator log | actual CI/local result required |
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
SystemVerilog unit/integration regression
        ↓
Verilator lint
        ↓
Vivado synthesis/implementation (only with explicit target)
        ↓
board-specific proof
```
