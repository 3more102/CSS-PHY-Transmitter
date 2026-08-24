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
- strict warning-fatal Verilator `-Wall` lint
- GitHub Actions verification with Icarus Verilog + Verilator
- evidence-integrity gate that rejects incomplete RTL/lint results
- Vivado synthesis/implementation flow that refuses to invent an FPGA target

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

When Icarus Verilog is unavailable but ModelSim/Questasim (`vlib`/`vlog`/`vsim`)
is installed, the identical regression matrix runs through:

```bash
make rtl-msim
```

The ModelSim driver applies the same strictness contract: every invocation must
exit 0, every test must emit its expected PASS marker, and any `** Error`,
`** Failure` or `** Fatal` diagnostic fails the regression (older ModelSim
builds exit 0 even after `$fatal`, so transcript scanning is mandatory there).

Run strict Verilator lint:

```bash
make lint
```

The committed verification driver distinguishes `PASS`, `FAIL`, `SKIP`, and `BLOCKED`; missing tools are never reported as PASS. GitHub Actions additionally runs `scripts/require_ci_evidence.py`, which requires the open-source HDL stages to actually execute and pass.

### Established source/reference evidence

The tool-independent regression executes **46 Python tests** and establishes:

- exact supplied 1 Mbps/250 kbps codeword-table agreement;
- exact supplied 152-real + 152-imag m=1 chirp-vector agreement;
- all four generated chirp ROMs match the reference equations;
- bit ordering across PHR, payload, DEMUX, symbol mapping, interleaver and final stream;
- both PHY rates and payload matrix 0, 1, 3, 25 and 127 bytes;
- deterministic randomized equivalence with seed `0x802154`;
- six-bit `floor` quantization MSE = **0.000891330083552**, below the required `0.005` threshold.

### Executed open-source HDL evidence

GitHub Actions has executed the Icarus/Verilator flow successfully. The CI evidence gate requires:

- every unit-test PASS marker;
- protocol PASS for both rates;
- controller and top-level PASS for payloads `0, 1, 3, 25, 127` at both rates;
- back-to-back multi-packet PASS for both rates (three sequential packets,
  including equal-length packets with distinct payload contents, verifying
  packet-to-packet state cleanup);
- fixed-point MSE acceptance;
- strict Verilator `-Wall` success with warnings treated as fatal;
- no Verilator warning/error diagnostics in the preserved lint log.

Synthesis/timing remains target-dependent and is not fabricated.

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
