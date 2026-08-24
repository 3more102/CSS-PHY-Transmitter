#!/usr/bin/env python3
"""MSE accuracy evidence (assignment Section 3.3 / 6).

Computes, per the reference document definition:

    meanSquareError = sum(|exact - fixed|^2) / sum(|exact|^2)

two quantities:

  A. Chirp-sequence MSE (N = 152 samples per chirp sequence, one value per
     chirp index m = 1..4): floating-point chirp samples from
     chirpSequenceGenerator() vs the fixed-point quantization actually used
     by the RTL ROM, floor(sample * (2^6-1 - 1)) per runMe.m.

  B. Full-chain MSE: complete transmitter output stream with floating-point
     chirps vs the committed fixed-point golden vectors, for every official
     regression case.

The acceptance threshold from IEEE 802.15.4 Section 6.5a.5.1 is 0.005.
This script does NOT measure RTL-vs-golden equality; that is a separate,
stricter bit-exact criterion covered by the ModelSim regression.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import gen_golden_vectors as g

THRESHOLD = 0.005


def rel_mse(exact, fixed):
    num = sum((e.real - f.real) ** 2 + (e.imag - f.imag) ** 2
              for e, f in zip(exact, fixed))
    den = sum(e.real ** 2 + e.imag ** 2 for e in exact)
    return num / den


DAC_MAX = g.DAC_MAX   # 31, runMe.m: floor(chirpSequence * (2^(TxDACbitNumber-1)-1))


def main():
    failures = 0

    print("A. chirp-sequence MSE (floating vs fixed, N=152 per sequence)")
    print("   %-4s %-14s %s" % ("m", "MSE", "status"))
    worst_a = 0.0
    for m in (1, 2, 3, 4):
        seqs = g.chirp_sequence(m)                 # list of 4 subchirps x 38
        exact = [s for col in seqs for s in col]   # 152 complex samples
        q = g.quantize(seqs)
        # dequantize to floating-point amplitude (runMe.m's commented
        # normalization: chirpSequence_Tx / (2^(TxDACbitNumber-1)-1)) so the
        # comparison is at a common scale, per the reference MSE definition
        fixed = [complex(r / DAC_MAX, i / DAC_MAX) for col in q for r, i in col]
        mse = rel_mse(exact, fixed)
        worst_a = max(worst_a, mse)
        ok = mse < THRESHOLD
        if not ok:
            failures += 1
        print("   %-4d %-14.3e %s" % (m, mse, "PASS" if ok else "FAIL"))

    print()
    print("B. full-chain output MSE (floating-chirp chain vs fixed-point")
    print("   golden vectors), per official regression case")
    cases = [(0, 20, 1), (0, 55, 1), (0, 127, 1),
             (1, 20, 1), (1, 55, 1), (1, 127, 1),
             (0, 25, 2), (1, 40, 4)]
    worst_b = 0.0
    for case_id, (rate, plen, m) in enumerate(cases):
        ci, cq = g.tx_chips(plen, rate, case_seed=case_id)

        def chain(chirp_float):
            # identical DQPSK/DQCSK arithmetic but with unquantized chirps
            gap_lo = g.TCHIRP - 4 * g.TSUB - 2 * g.TAU_SAMPLES[m - 1]
            gap_hi = g.TCHIRP - 4 * g.TSUB + 2 * g.TAU_SAMPLES[m - 1]
            cum = [0, 0, 0, 0]
            re_out, im_out = [], []
            grp = 0
            import math
            for base in range(0, len(ci), 4):
                for k in range(4):
                    step = {(1, 1): 0, (0, 1): 2, (1, 0): -2, (0, 0): 4}[
                        (ci[base + k], cq[base + k])]
                    cum[k] = (cum[k] + step) % 8
                    u = (1 + cum[k]) % 8
                    a = round(math.cos(u * math.pi / 4))
                    b = round(math.sin(u * math.pi / 4))
                    for s in chirp_float[k]:
                        sr, si = s.real, s.imag
                        re_out.append(a * sr - b * si)
                        im_out.append(b * sr + a * si)
                gap = gap_lo if grp % 2 == 0 else gap_hi
                re_out += [0.0] * gap
                im_out += [0.0] * gap
                grp += 1
            return re_out, im_out

        seqs = g.chirp_sequence(m)
        flt = [[complex(s) for s in col] for col in seqs]
        re_f, im_f = chain(flt)
        tag = "rate%d_len%d_m%d" % (rate, plen, m)
        lines = open(os.path.join(g.VEC, "golden_%s.hex" % tag)).read().split()

        def s8(h):
            v = int(h, 16)
            return v - 256 if v >= 128 else v

        # golden samples are DAC-scale integers; dequantize to amplitude
        # scale so both sides of the comparison share units
        gold_i = [s8(l[:2]) / DAC_MAX for l in lines]
        gold_q = [s8(l[2:]) / DAC_MAX for l in lines]
        assert len(re_f) == len(gold_i) == len(gold_q)
        num = sum((r - gi) ** 2 + (im - gq) ** 2
                  for r, im, gi, gq in zip(re_f, im_f, gold_i, gold_q))
        den = sum(r * r + im * im for r, im in zip(re_f, im_f))
        mse = num / den
        worst_b = max(worst_b, mse)
        ok = mse < THRESHOLD
        if not ok:
            failures += 1
        print("   %-18s n=%-7d MSE=%.3e %s"
              % (tag, len(re_f), mse, "PASS" if ok else "FAIL"))

    print()
    print("worst chirp MSE      : %.3e" % worst_a)
    print("worst full-chain MSE : %.3e" % worst_b)
    print("threshold            : %.3f" % THRESHOLD)
    print("RESULT: %s (%d failures)" % ("PASS" if failures == 0 else "FAIL",
                                        failures))
    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
