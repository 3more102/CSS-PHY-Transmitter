# Root-Cause Report: RTL vs Golden Sample Mismatches (all regression cases)

Second-session independent verification, 2026-08-24.
Branch: `verify/codeword-bit-order` (isolated worktree), base HEAD `2efd326`.

## Summary

Two independent defects were found and verified. After both fixes, the full
8-case golden-vector regression passes with exact sample-by-sample equality
(0 tolerance).

## Defect 1 (RTL): codeword bit-order reversed at serialization

FILE   : rtl/css_codeword_rom.v (+ one line in rtl/css_pkt_ctrl.v)
BLOCK  : codeword ROM -> chunk buffer -> parallel-to-serial converter
FIRST BAD INPUT : first non-palindromic data codeword
                  (rate0_len20_m1: global bit address 24, chip 64, group 16)
EXPECTED: codeword chips serialized c0,c1,c2,c3 (MATLAB ChirpSpreadSpectrum_Tx.m
          "least significant chip c0 is processed first")
ACTUAL : c3,c2,c1,c0 (bit-reversed)

ROOT CAUSE:
The bi-orthogonal tables store each codeword in *text order* (c0 = MSB):
`m4[1] = 4'b1010`, and `cw32.hex` rows are written by
`int("".join(chips), 2)` so c0 lands on bit 31. The chunk buffers are written
as `{{60{1'b0}}, cw[3:0]}` (codeword at bits [3:0]) and serialized LSB-first
(`buf_i[buf_sel][ser_cnt]`, ser_cnt ascending). The result is that every
codeword is emitted reversed. This went undetected because the first four
data codewords of the len=20 vector are palindromes (I/Q patterns like
1001, 0110, 1111, 0000) - divergence first appears at data codeword #4,
which had shown up as a mid-packet "rotation" failure at sample ~3073.

For 250 kb/s the same reversal corrupts the interleaver input: the
interleaver permutation assumes `comb[]` indexes follow the MATLAB combined
order [c0..c31 | d0..d31].

FIX (verified):
1. rtl/css_codeword_rom.v: store c0 at bit 0 - reverse the m4 literals and
   bit-reverse each m32 entry after `$readmemh`.
2. rtl/css_pkt_ctrl.v: `comb_{i,q} = {cw_*_rom, cw_even_*}` so comb[0..31]
   = even codeword c0..c31 and comb[32..63] = odd codeword d0..d31, matching
   the MATLAB interleaver index convention exactly (perm table unchanged).

EVIDENCE: per-chunk comparison of DUT-consumed chip stream vs reference:
9 chunks matched directly (palindromes), 20 matched exactly when reversed,
0 neither. After fix: all match directly.

## Defect 2 (vectors): golden generator payload-seed mismatch

FILE   : scripts/gen_golden_vectors.py
BLOCK  : stimulus/golden consistency
ROOT CAUSE: `tx_chips()` called `payload_stimulus(payload_len)` with the
default seed=0, while `payload_*.hex` files were written with
seed=case_id. Only case_id=0 (rate0_len20_m1) was self-consistent; for the
other seven vectors the golden stream was computed from a DIFFERENT payload
than the DUT consumes.
FIX: pass case_seed through tx_chips(); regenerate all vectors/.
Cross-checked sample-exact against an independent second implementation
(scripts/verify_ref_model.py, written directly from the MATLAB sources).

## Verification after fixes

ModelSim ASE 18.1, tb_css_tx_top, exact equality:

| case            | samples | result |
|-----------------|---------|--------|
| rate0_len20_m1  | 7842    | PASS   |
| rate0_len55_m1  | 16896   | PASS   |
| rate0_len127_m1 | 35328   | PASS   |
| rate1_len20_m1  | 29184   | PASS   |
| rate1_len55_m1  | 62976   | PASS   |
| rate1_len127_m1 | 136704  | PASS   |
| rate0_len25_m2  | 9216    | PASS   |
| rate1_len40_m4  | 47616   | PASS   |

Before: 0/8 passed (2849..136000 mismatching samples per case).

## Stage audit results (all verified against MATLAB sources)

- PHR bit order: LSB-of-length first (`payloadLength_Binary(7:-1:1)` reverse
  assignment) - RTL correct, matches dbg_bit.log addr 0..11.
- Payload bytes MSB-first within byte - RTL correct.
- Zero padding 6/24 - correct.
- Even bit->I / odd bit->Q demux - correct.
- Symbol mapper (3->4, 6->32, binary2decimal first-bit-MSB) - correct.
- Interleaver perm indices - correct once comb ordering fixed.
- Preamble/SFD tables incl. latching order - correct.
- QPSK mapping ((I+Q)-j(I-Q))/2 step table - correct.
- DQPSK 4-lane feedback, exp(j*pi/4) start (u=1+cum, mod 8) - correct.
- CSK gaps Teven/Todd per chirp index, zero-filled gap samples - correct.
- Chirp ROM contents/quantization (floor, 6-bit) - correct.

## Helper artifacts added

- scripts/verify_ref_model.py  - independent MATLAB-faithful golden model + stage vectors
- scripts/analyze_divergence.py- per-(group,lane) rotation inference from DUT dumps
