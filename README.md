# CSS PHY Transmitter — IEEE 802.15.4 FPGA/RTL Project

Synthesizable IEEE 802.15.4 Chirp Spread Spectrum (CSS) PHY transmitter derived from the supplied assignment, CSS reference document, and MATLAB floating/fixed-point model.

## Implemented

- 1 Mbps and 250 kbps CSS modes (`DATA_RATE` parameter)
- PSDU lengths 0..127 bytes
- 12-bit PHR and MATLAB-exact zero-padding behavior
- I/Q DEMUX
- 1 Mbps 3→4 and 250 kbps 6→32 bi-orthogonal mapping
- exact 250 kbps interleaver
- preamble + rate-specific SFD
- QPSK + four-symbol DQPSK feedback
- four 152-sample, 6-bit signed chirp ROMs
- even/odd CSK gaps and complex modulation
- signed 8-bit `Tx_real` / `Tx_imag`
- deterministic Python reference model and golden-vector generation
- unit and full-chain self-checking SystemVerilog testbenches
- deterministic randomized regression
- Vivado synthesis/implementation flow that refuses to invent an FPGA target
- GitHub Actions verification with Icarus Verilog + Verilator

## Top-level interface

`rtl/css_phy_tx_top.sv` exposes:

```text
clk
reset
start_Tx
payloadLength[7:0]
payload_wr_en
payload_addr[6:0]
payload_din[7:0]
done_Tx
Tx_real[7:0]
Tx_imag[7:0]
```

The three payload-write signals are the minimum explicit extension required to populate the assignment payload RAM before `start_Tx`.

## Verification

Run all locally available checks:

```bash
make verify
```

Run RTL regression directly:

```bash
make rtl
```

Run Verilator lint:

```bash
make lint
```

The committed verification driver distinguishes `PASS`, `FAIL`, `SKIP`, and `BLOCKED`; missing tools are never reported as PASS.

### Established source/reference evidence

Before publication, the tool-independent regression executed **46 Python tests with 0 failures**. It established:

- exact supplied 1 Mbps/250 kbps codeword-table agreement;
- exact supplied 152-real + 152-imag m=1 chirp-vector agreement;
- all four generated chirp ROMs match the reference equations;
- bit ordering across PHR, payload, DEMUX, symbol mapping, interleaver and final stream;
- both PHY rates and payload matrix 0, 1, 3, 25 and 127 bytes;
- deterministic randomized equivalence with seed `0x802154`;
- six-bit `floor` quantization MSE = **0.000891330083552**, below the required `0.005` threshold.

RTL simulator/lint status is determined by actual local or CI execution; synthesis/timing remains target-dependent and is not fabricated.

## Fixed point

The supplied fixed-point MATLAB transmitter uses:

```text
signed chirp width: 6 bits
quantization: floor
```

The normalized m=1 chirp MSE reproduced by the committed script is:

```text
0.000891330083552 < 0.005
```

Regenerate it with:

```bash
python3 matlab/mse/mse_analysis.py
```

## Synthesis

No FPGA part is hard-coded. With Vivado and a confirmed target:

```bash
FPGA_PART=<exact-part> CLOCK_PERIOD_NS=31.250 \
  vivado -mode batch -source scripts/vivado_synth.tcl

FPGA_PART=<exact-part> \
  vivado -mode batch -source scripts/vivado_impl.tcl
```

No LUT/FF/BRAM/DSP, WNS/TNS, Fmax, power, bitstream, or board result is claimed until those tools and a real target are used.

## Repository structure

```text
rtl/                    synthesizable SystemVerilog
rtl/rom/                generated codeword/chirp ROM contents
tb/                     self-checking SystemVerilog tests
tests/                  Python reference/architecture/static tests
matlab/vector_generation/ executable reference + deterministic vectors
matlab/mse/              fixed-point MSE analysis
matlab/original/         minimal numerical source vectors used for regression
scripts/                 verification/lint/Vivado/report tooling
constraints/             timing-only configurable XDC
docs/                    architecture, bit-order, fixed-point and status docs
.github/workflows/       open-source HDL CI
```

The original assignment/reference PDF, DOCX and ZIP are not republished in this public repository; only the minimal numerical vectors needed to reproduce the checks are included.
