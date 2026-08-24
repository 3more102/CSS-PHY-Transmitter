# Defect Report D-1: `busy` never deasserts after a packet (done_Tx defect)

Status      : OPEN - reproduced, root-caused, NOT patched in this release session
Discovered  : 2026-08-24, release-evidence session (worktree CSS_PHY_RTL_release),
              by the new control/restart testbench (item 13 of the release audit)
Reproducer  : `tb/tb_control_restart.v` + repro log
              `reports/defect_busy_stuck_repro.log`
Severity    : Major for multi-packet use / assignment `done_Tx` requirement.
              Single-packet streaming behavior is unaffected: every committed
              golden-vector result remains valid.

## Symptom

After any packet completes (o_eop asserted, output stream correct and
complete), `css_pkt_ctrl` keeps `busy = 1` forever. Consequences:

- the controller never returns to ST_IDLE;
- a second `start` pulse is ignored (`begin_pkt` requires `busy` falling
  edge in M_IDLE) - back-to-back packets are impossible without reset;
- no `done_Tx`-equivalent deassertion exists.

The official regression never observed this because `tb_css_tx_top` checks
only the sample stream and never re-starts the DUT or inspects `busy`.

## Root cause (RTL reading + simulation confirmed)

1. `rtl/css_dqcsk_mod.v` lines ~80-88:
   the advance request to the packet controller is

   ```verilog
   wire adv_int = (state == M_PLAY) && (play_cnt == TSUB - 2) &&
                  busy && !last_r;     // <-- gated off for the FINAL chip
   ```

   For the final chip `last_r = 1`, so **no chip_latch pulse is ever issued
   for the last chip position**.

2. `rtl/css_pkt_ctrl.v`, advance-on-latch block:
   `finishing <= 1'b1` is reachable only inside
   `if (st == ST_RUN && chip_latch)` when `phase == PH_DATA &&
   ser_cnt == chunk_len_m1 && chunks_left == 8'd1`. Since condition 1
   guarantees that latch never occurs at that position, `finishing` is
   dead logic and the `ST_RUN -> if (finishing) busy <= 0` transition
   can never fire.

## Evidence

`reports/defect_busy_stuck_repro.log`:

```
# TB ERROR [pkt1]: busy did not fall after eop        <- first packet
# TB ERROR [pkt2]: sop never asserted                  <- second start ignored
# TB ERROR [pkt2]: eop missing
# TB ERROR [pkt2]: sample count 0 != expected 32256
```

Packet 1's 7842-sample stream itself verified bit-exact before the stall,
confirming datapath correctness; only the control hand-off is broken.

## Required fix direction (for a future RTL session, not applied here)

Issue one final latch/finish event for the last chip (e.g. drop the
`!last_r` gate on a dedicated finish request, or set `finishing`
combinationally from `chip_last && consume`), then re-run:
official 8/8, edge 10/10, serialization 72/72, plus
`tb_control_restart` expecting PASS.

## Related finding (fixed in this session, sim-only)

D-2: the codeword ROM missing-file guard could never fire because `m32`
is zero-filled *before* `$readmemh`, so a missing `cw32.hex` left no X
residue. Fixed with a sim-only shadow word inside
`synthesis translate_off` guards (`rtl/css_codeword_rom.v`); negative test
now prints FATAL, positive behavior unchanged (full regression re-run:
8/8 exact). The earlier integration report's claim that this guard was
verified was incorrect for the codeword ROM.
