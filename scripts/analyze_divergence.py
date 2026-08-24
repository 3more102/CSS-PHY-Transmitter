#!/usr/bin/env python3
"""Analyze RTL-vs-golden divergence structure per chirp group/lane.

Infers, for every (group, lane) subchirp window, the rotation unit u used
by the DUT by correlating its samples against the quantized chirp table,
then compares against the golden expectation.
"""
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIMD = os.path.join(ROOT, "sim_verify")
VEC = os.path.join(ROOT, "vectors")

TSUB = 38
TAU = [15, 10, 5, 0]


def load(path, width=8):
    out = []
    half = 1 << (width - 1)
    full = 1 << width
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        vals = []
        for lo in (0, 2):
            v = int(line[lo:lo + 2], 16) % full
            vals.append(v - full if v >= half else v)
        out.append(tuple(vals))
    return out


def chirp_table(m):
    """quantized chirp ROM: table[k][n] = (re, im)"""
    tab = [[], [], [], []]
    path = os.path.join(VEC, "chirp_rom.hex")
    lines = [l.strip() for l in open(path) if l.strip()]
    for idx, line in enumerate(lines):
        bank = idx // (4 * TSUB)
        if bank != m - 1:
            continue
        rem = idx % (4 * TSUB)
        k = rem // TSUB
        n = rem % TSUB
        r = int(line[0:2], 16)
        im = int(line[2:4], 16)
        r = r - 64 if r > 31 else r
        im = im - 64 if im > 31 else im
        tab[k].append((r, im))
    return tab


def infer_u(samples, k_tab):
    """Try all 8 rotations, return best u and max abs error."""
    best = None
    for u in range(8):
        a = [[1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1], [0, -1], [1, -1]][u]
        ca, cb = a
        err = 0
        for (sr, si), (gr, gi) in zip(k_tab, samples):
            pr = ca * sr - cb * si
            pi = cb * sr + ca * si
            err += abs(pr - gr) + abs(pi - gi)
        if best is None or err < best[1]:
            best = (u, err)
    return best


def main():
    rate, plen, m = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    tag = "rate%d_len%d_m%d" % (rate, plen, m)
    dut = load(os.path.join(SIMD, "dut_%s.hex" % tag), 7)
    gold = load(os.path.join(VEC, "golden_%s.hex" % tag))
    tab = chirp_table(m)

    gap_lo = 192 - 152 - 2 * TAU[m - 1]
    gap_hi = 192 - 152 + 2 * TAU[m - 1]

    # group layout (includes per-group time gaps)
    pos = 0
    groups = []
    gidx = 0
    while pos + 152 <= len(gold):
        groups.append(pos)
        pos += 152 + (gap_lo if gidx % 2 == 0 else gap_hi)
        gidx += 1

    print("samples: dut=%d gold=%d groups=%d" % (len(dut), len(gold), len(groups)))
    first_bad = None
    for g, start in enumerate(groups):
        gap = gap_lo if g % 2 == 0 else gap_hi
        ug = []
        for k in range(4):
            s = start + k * TSUB
            win_d = dut[s:s + TSUB]
            win_g = gold[s:s + TSUB]
            ud = infer_u(win_d, tab[k])
            gg = infer_u(win_g, tab[k])
            ug.append((ud[0], gg[0]))
            if ud[0] != gg[0] and first_bad is None:
                first_bad = (g, k, s, ud[0], gg[0])
        if any(a != b for a, b in ug):
            print("group %3d start %5d lanes(u_dut,u_gold): %s" %
                  (g, start, ug))
    print("first divergent subchirp:", first_bad)


if __name__ == "__main__":
    main()
