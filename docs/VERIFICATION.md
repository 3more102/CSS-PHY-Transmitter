# Verification

## One-command evidence run

```bash
make verify
```

Status semantics are strict:

- `PASS`: command actually executed successfully;
- `FAIL`: command actually executed and failed;
- `SKIP`: intentionally not applicable;
- `BLOCKED`: required external tool/target unavailable.

## Tool-independent evidence

The pre-publication regression executed **46 Python tests with 0 failures** covering exact source tables/vectors, all four chirp ROMs, PHR/payload bit ordering, padding, DEMUX, mapper ordering, interleaver permutation, QPSK, DQPSK, even/odd gaps, MSE, both rates, required payload matrix, all payload lengths for grouping validity, deterministic randomized equivalence, signed 8-bit range, and report-parser/static build checks.

## HDL testbenches

The `tb/` suite contains self-checking tests for all major blocks plus controller, protocol/reset/start behavior, and full transmitter sample streams for:

```text
1 Mbps:   payload 0, 1, 3, 25, 127 bytes
250 kbps: payload 0, 1, 3, 25, 127 bytes
```

Run:

```bash
make rtl
```

The target regenerates deterministic vectors before simulation.

## MSE evidence

```text
normalized MSE = 0.000891330083552
required bound = 0.005
result          = PASS
```

This value is recalculated by `python3 matlab/mse/mse_analysis.py`; it is not hard-coded as a test result.

## CI

`.github/workflows/verify.yml` installs Icarus Verilog and Verilator, runs `make verify`, and preserves verification evidence as workflow artifacts. CI is considered PASS only when an actual workflow run succeeds.

## EDA evidence policy

Vivado synthesis/implementation runs only when Vivado is available and `FPGA_PART` is explicitly supplied. Timing is accepted only with a real `sys_clk` constraint. No utilization, timing, Fmax, power, bitstream, or on-board PASS is claimed without actual evidence.
