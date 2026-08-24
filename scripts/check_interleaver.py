#!/usr/bin/env python3
"""Static interleaver audit.

Extracts the `perm` function from rtl/css_pkt_ctrl.v and verifies:
  1. it equals the MATLAB bitInterleaver output_indices verbatim;
  2. its derived 4-bit group order equals
     G0 G13 G2 G15 G4 G9 G6 G11 G8 G5 G10 G7 G12 G1 G14 G3.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MATLAB_IDX = [0, 1, 2, 3, 52, 53, 54, 55, 8, 9, 10, 11, 60, 61, 62, 63,
              16, 17, 18, 19, 36, 37, 38, 39, 24, 25, 26, 27, 44, 45, 46, 47,
              32, 33, 34, 35, 20, 21, 22, 23, 40, 41, 42, 43, 28, 29, 30, 31,
              48, 49, 50, 51, 4, 5, 6, 7, 56, 57, 58, 59, 12, 13, 14, 15]

EXPECTED_GROUPS = [0, 13, 2, 15, 4, 9, 6, 11, 8, 5, 10, 7, 12, 1, 14, 3]


def main():
    src = open(os.path.join(ROOT, "rtl", "css_pkt_ctrl.v")).read()
    m = re.search(r"function\s*\[5:0\]\s*perm;(.*?)endfunction", src, re.S)
    if not m:
        print("FAIL: perm() not found")
        sys.exit(1)
    pairs = re.findall(r"6'd(\d+):\s*perm\s*=\s*6'd(\d+)", m.group(1))
    perm = {int(a): int(b) for a, b in pairs}
    dflt = re.search(r"default:\s*perm\s*=\s*6'd(\d+)", m.group(1))
    if dflt:
        dv = int(dflt.group(1))
        for j in range(64):
            perm.setdefault(j, dv)
    if len(perm) != 64 or sorted(perm) != list(range(64)):
        print("FAIL: perm table incomplete (%d entries)" % len(perm))
        sys.exit(1)

    out_ok = all(perm[j] == MATLAB_IDX[j] for j in range(64))
    print("perm == MATLAB output_indices:", "PASS" if out_ok else "FAIL")

    groups = [perm[4 * j] // 4 for j in range(16)]
    grp_ok = (groups == EXPECTED_GROUPS and
              all(perm[4 * j + k] == perm[4 * j] + k
                  for j in range(16) for k in range(4)))
    print("output group order %s:" % groups, "PASS" if grp_ok else "FAIL")
    sys.exit(0 if (out_ok and grp_ok) else 1)


if __name__ == "__main__":
    main()
