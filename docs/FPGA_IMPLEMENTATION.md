# FPGA Synthesis / Implementation

## Status: BLOCKED — no FPGA target supplied

No exact target FPGA part or board pinout exists in this repository, and none is invented.
Consequently this repository contains **no** utilization, WNS/TNS, Fmax, power, bitstream,
or on-board results of any kind.

The historical reference used a Xilinx Spartan-3A device; that historical device is
deliberately **not** adopted as this project's target.

### Precise blocker statement

Synthesis was never run on the development workstation used to author this repository.
Verified machine facts:

- `vivado` is not on `PATH` (`where.exe vivado` finds nothing).
- `C:\Xilinx` exists but contains only the Xilinx Information Center stub (`xic`); a
  recursive search for `vivado.exe` / `vivado.bat` under `C:\Xilinx` returns zero matches.
- No Quartus installation exists under `C:\intelFPGA*` (ModelSim only).

Because no Vivado executable is reachable, synthesis, implementation, and timing closure
are **NOT RUN**. This is a tooling/input blocker only; nothing about the RTL is claimed
about hardware behavior beyond simulation.

### Exact missing inputs (what unblocks the flow)

1. `FPGA_PART` — exact Vivado part name (e.g. from a board file), not a family name.
2. Target board identification.
3. Oscillator / clock input pin and its board trace properties.
4. IOSTANDARD for every used I/O bank pin.
5. Reset and start interface pins.
6. Destination of `Tx_real` / `Tx_imag` outputs (DAC part pins, or test-header pins).

Until items 1–6 are supplied by the project owner, no LOC/IOSTANDARD constraint may be
written and no bitstream may be generated.

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

Synthesis (bash):

```bash
FPGA_PART=<exact-part> CLOCK_PERIOD_NS=31.250 \
  vivado -mode batch -source scripts/vivado_synth.tcl
```

Synthesis (PowerShell):

```powershell
$env:FPGA_PART = "<exact-part>"; $env:CLOCK_PERIOD_NS = "31.250"
vivado -mode batch -source scripts/vivado_synth.tcl
```

Implementation (bash):

```bash
FPGA_PART=<exact-part> \
  vivado -mode batch -source scripts/vivado_impl.tcl
```

Implementation (PowerShell):

```powershell
$env:FPGA_PART = "<exact-part>"
vivado -mode batch -source scripts/vivado_impl.tcl
```

Metrics extraction (after implementation):

```bash
python scripts/parse_vivado_reports.py --report-dir reports/implementation \
  --output reports/implementation/impl_metrics.json
```

Flow integrity rules enforced by the scripts:

- Both Tcl entry points hard-error if `FPGA_PART` is unset or empty.
- The implementation script verifies that the requested `FPGA_PART` matches the part
  recorded inside the post-synthesis checkpoint before producing any evidence.
- Each run writes a provenance manifest (`synth_manifest.txt`, `impl_manifest.txt`)
  recording part, top module, generics, clock settings, and the Vivado version, so
  reports can always be attributed to the configuration that produced them.
- Report directories are deterministic (fixed paths); reruns overwrite them, which is why
  manifests are written on every run.

## Expected artifacts after a real run

```text
reports/synthesis/synth_utilization.rpt            (also _hier.rpt)
reports/synthesis/synth_timing_summary.rpt
reports/synthesis/synth_clock_utilization.rpt
reports/synthesis/synth_methodology.rpt
reports/synthesis/synth_check_timing.rpt
reports/synthesis/synth_clocks.txt
reports/synthesis/synth_manifest.txt
results/vivado/css_phy_tx_post_synth.dcp
reports/implementation/impl_utilization.rpt        (also _hier.rpt)
reports/implementation/impl_timing_summary.rpt
reports/implementation/impl_clock_utilization.rpt
reports/implementation/impl_drc.rpt
reports/implementation/impl_methodology.rpt
reports/implementation/impl_route_status.rpt
reports/implementation/impl_check_timing.rpt
reports/implementation/impl_clocks.txt
reports/implementation/impl_manifest.txt
reports/implementation/impl_metrics.json           (parser output)
results/vivado/css_phy_tx_post_route.dcp
```

Any utilization/timing numbers must appear inside these files together with their
manifests. Numbers quoted anywhere else do not count as evidence.

## Clocking

The CSS waveform reference uses 32 MHz sampling, so the default timing constraint is
31.250 ns. For a 32 MHz system clock use `SAMPLE_DIV=1`; for an integer multiple use
`SAMPLE_DIV=fclk/32MHz`. A non-integer ratio requires a proper fractional/sample-tick
architecture and must not be approximated silently.

`constraints/css_phy_tx.xdc` contains timing only. It intentionally contains no LOC or
IOSTANDARD values because no board is identified.

## Timing-closure checklist ("closure" counts only when ALL hold)

- [ ] Synthesis completed with no `ERROR:` messages; checkpoint written.
- [ ] Implementation completed with no `ERROR:` messages; route fully routed per
      `impl_route_status.rpt`.
- [ ] `sys_clk` present: exactly one clock, period as configured (31.250 ns default).
- [ ] WNS >= 0 and TNS == 0 at both min and max analysis in `impl_timing_summary.rpt`.
- [ ] Zero unconstrained paths (`-report_unconstrained` section empty).
- [ ] `report_drc`: no critical warnings / errors.
- [ ] `check_timing` output reviewed; no unexplained exceptions.
- [ ] Utilization recorded for LUT / FF / BRAM / DSP / IO / BUFG in
      `impl_utilization.rpt`.
- [ ] `python scripts/parse_vivado_reports.py` exits 0 with
      `timing_status == "PASS"` in `impl_metrics.json`.
- [ ] Manifests present and consistent with the part actually targeted.

The parser exit codes are: 0 = measured PASS, 1 = FAIL or unconstrained paths,
2 = evidence missing/unrecognized. Absence of evidence never counts as success.

## Before bitstream generation

Confirm the exact FPGA part/board, oscillator and clock input pin, I/O standards,
reset/start interface pins, payload-loading demonstration interface, destination of
`Tx_real`/`Tx_imag`, and all board-specific electrical constraints.
