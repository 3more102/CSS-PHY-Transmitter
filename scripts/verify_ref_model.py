#!/usr/bin/env python3
"""Independent re-implementation of the MATLAB fixed-point CSS PHY Tx,
written directly from matlab/original/... sources (second-session audit).

Purpose:
  1. cross-check vectors/golden_*.hex produced by gen_golden_vectors.py
  2. provide stage-level expectations (chips, QPSK steps, DQPSK units)
     for localizing RTL divergence.

Usage: python scripts/verify_ref_model.py <rate> <plen> <m>
"""
import cmath
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VEC = os.path.join(ROOT, "vectors")

FS = 32.0
TSUB = 38
TCHIRP = 192
DAC_MAX = 31
MU = 7.3158
PHR_LEN = 12
PREAMBLE_LEN = [32, 80]
SFD_M = [
    [-1, 1, 1, 1, -1, 1, -1, -1, 1, -1, -1, 1, 1, 1, -1, -1],
    [-1, 1, 1, 1, 1, -1, 1, -1, -1, -1, 1, -1, -1, -1, 1, 1],
]
TAU = [15, 10, 5, 0]          # Tau_m * fs for m=1..4


def raised_cosine():
    n_ones = 12
    tmp = [1.0] * n_ones
    for n in range(12, 19 + 1):
        tmp.append(0.5 * (1 + math.cos(5 * math.pi / TSUB * (n - 11.4))))
    return list(reversed(tmp)) + tmp[1:19]


def chirp_seq(m):
    zeta = [[1, 1, -1, -1], [1, -1, 1, -1], [-1, -1, 1, 1], [-1, 1, -1, 1]][m - 1]
    fkm = [[-3.15, 3.15, 3.15, -3.15], [3.15, -3.15, -3.15, 3.15],
           [-3.15, 3.15, 3.15, -3.15], [3.15, -3.15, -3.15, 3.15]][m - 1]
    rc = raised_cosine()
    cols = []
    for k in range(4):
        col = []
        for t in range(-19, 19):
            arg = fkm[k] + MU * zeta[k] / 2 / FS * t
            col.append(cmath.exp(2j * math.pi / FS * arg * t) * rc[t + 19])
        cols.append(col)
    return cols


def quant(cols):
    return [[(int(math.floor(s.real * DAC_MAX)), int(math.floor(s.imag * DAC_MAX)))
             for s in col] for col in cols]


def payload_stimulus(length, seed=0):
    state = 0x2B + seed * 7919

    def rnd():
        nonlocal state
        for _ in range(8):
            bit = ((state >> 15) ^ (state >> 13) ^ (state >> 12) ^ (state >> 10)) & 1
            state = ((state << 1) | bit) & 0xFFFF
        return state & 0xFF
    rnd()
    return [rnd() for _ in range(length)]


def phr_bits(plen):
    # MATLAB: payloadLength_Binary(7:-1:1) = decimal2binary(len,7,1)
    # decimal2binary returns dec2bin transposed -> MSB-first string order;
    # the (7:-1:1) assignment reverses it => LSB transmitted first.
    s = format(plen, '07b')
    msb_first = [int(c) for c in s]
    return list(reversed(msb_first)) + [0, 0] + [0, 0, 0]


def hadamard(n):
    h = [[1]]
    while len(h) < n:
        h = [row + row for row in h] + [row + [-x for x in row] for row in h]
    return h


def cw_table(n):
    std = hadamard(n)
    return [[(x + 1) // 2 for x in r] for r in std] + \
           [[(-x + 1) // 2 for x in r] for r in std]


OUT_IDX = [0, 1, 2, 3, 52, 53, 54, 55, 8, 9, 10, 11, 60, 61, 62, 63,
           16, 17, 18, 19, 36, 37, 38, 39, 24, 25, 26, 27, 44, 45, 46, 47,
           32, 33, 34, 35, 20, 21, 22, 23, 40, 41, 42, 43, 28, 29, 30, 31,
           48, 49, 50, 51, 4, 5, 6, 7, 56, 57, 58, 59, 12, 13, 14, 15]


def chips_and_stream(rate, plen, case_seed):
    pad = 6 - ((PHR_LEN + 8 * plen) % 6) if rate == 0 else \
        24 - ((PHR_LEN + 8 * plen) % 24)
    data = phr_bits(plen)
    for byte in payload_stimulus(plen, seed=case_seed):
        data += [(byte >> (7 - i)) & 1 for i in range(8)]
    data += [0] * pad

    i_path, q_path = data[0::2], data[1::2]
    bpcw = 3 if rate == 0 else 6
    ncw = len(i_path) // bpcw
    table = cw_table(4 if rate == 0 else 32)

    def dec(bits):  # binary2decimal.m: first element is MSB
        v = 0
        for b in bits:
            v = (v << 1) | b
        return v

    i_syms = [dec(i_path[n * bpcw:(n + 1) * bpcw]) for n in range(ncw)]
    q_syms = [dec(q_path[n * bpcw:(n + 1) * bpcw]) for n in range(ncw)]

    def ser(syms):
        words = [table[s] for s in syms]
        if rate == 1:
            out = []
            for b in range(0, len(words), 2):
                comb = words[b] + words[b + 1]
                out.append([comb[j] for j in OUT_IDX])
            return [c for w in out for c in w]
        return [c for w in words for c in w]

    pre = [1] * PREAMBLE_LEN[rate]
    sfd = [(s + 1) // 2 for s in SFD_M[rate]]
    ci = pre + sfd + ser(i_syms)
    cq = pre + sfd + ser(q_syms)
    return ci, cq


STEP = {(1, 1): 0, (0, 1): 2, (1, 0): 6, (0, 0): 4}  # 45-deg units, mod 8


def dqcsk(ci, cq, qchirp, m):
    gap_lo = TCHIRP - 152 - 2 * TAU[m - 1]
    gap_hi = TCHIRP - 152 + 2 * TAU[m - 1]
    cum = [0, 0, 0, 0]
    trace = []
    re_out, im_out = [], []
    for g in range(len(ci) // 4):
        for k in range(4):
            step = STEP[(ci[g * 4 + k], cq[g * 4 + k])]
            cum[k] = (cum[k] + step) % 8
            u = (1 + cum[k]) % 8
            a = round(math.cos(u * math.pi / 4))
            b = round(math.sin(u * math.pi / 4))
            trace.append((g, k, u))
            for (sr, si) in qchirp[k]:
                re_out.append(a * sr - b * si)
                im_out.append(b * sr + a * si)
        gap = gap_lo if g % 2 == 0 else gap_hi
        re_out += [0] * gap
        im_out += [0] * gap
    return re_out, im_out, trace


CASES = {(0, 20, 1): 0, (0, 55, 1): 1, (0, 127, 1): 2, (1, 20, 1): 3,
         (1, 55, 1): 4, (1, 127, 1): 5, (0, 25, 2): 6, (1, 40, 4): 7}


def main():
    rate, plen, m = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    tag = "rate%d_len%d_m%d" % (rate, plen, m)
    seed = CASES[(rate, plen, m)]
    ci, cq = chips_and_stream(rate, plen, seed)
    qc = quant(chirp_seq(m))
    re_s, im_s, _ = dqcsk(ci, cq, qc, m)

    def twos(v, w):
        return v & ((1 << w) - 1)

    mine = ["%02x%02x" % (twos(r, 8), twos(i, 8)) for r, i in zip(re_s, im_s)]
    gold = open(os.path.join(VEC, "golden_%s.hex" % tag)).read().split()
    n = min(len(mine), len(gold))
    bad = [k for k in range(n) if mine[k] != gold[k]]
    print("%s: mine=%d golden=%d first_diff=%s ndiff=%d" %
          (tag, len(mine), len(gold),
           bad[0] if bad else "none", len(bad)))
    if bad:
        k = bad[0]
        print("  sample %d mine=%s golden=%s" % (k, mine[k], gold[k]))


if __name__ == "__main__":
    main()
