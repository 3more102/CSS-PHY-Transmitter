# FPGA Synthesis / Implementation

## Current status

No exact target FPGA part or board pinout is assumed. Consequently this repository does not fabricate utilization, WNS/TNS, Fmax, power, bitstream, or on-board results.

The historical reference used a Xilinx Spartan-3A device; that historical device is not silently adopted as this project's target.

## Configurable Vivado flow

Required:

```text
FPGA_PART=<exact Xilinx part>
```

Optional:

```text
TOP=css_phy_tx_top
CLOCK_PORT=clk
CLOCK_PERIOD_NS=31.250
DATA_RATE=0|1
CHIRP_INDEX=1..4
SAMPLE_DIV=<integer >= 1>
```

Synthesis:

```bash
FPGA_PART=<exact-part> CLOCK_PERIOD_NS=31.250 \
  vivado -mode batch -source scripts/vivado_synth.tcl
```

Implementation:

```bash
FPGA_PART=<exact-part> \
  vivado -mode batch -source scripts/vivado_impl.tcl
```

The scripts create deterministic report directories and refuse target-dependent work without `FPGA_PART`.

## Clocking

The CSS waveform reference uses 32 MHz sampling, so the default timing constraint is 31.250 ns. For a 32 MHz system clock use `SAMPLE_DIV=1`; for an integer multiple use `SAMPLE_DIV=fclk/32MHz`. A non-integer ratio requires a proper fractional/sample-tick architecture and must not be approximated silently.

`constraints/css_phy_tx.xdc` contains timing only. It intentionally contains no LOC or IOSTANDARD values because no board is identified.

## Before bitstream generation

Confirm the exact FPGA part/board, oscillator and clock input pin, I/O standards, reset/start interface pins, payload-loading demonstration interface, destination of `Tx_real`/`Tx_imag`, and all board-specific electrical constraints.
