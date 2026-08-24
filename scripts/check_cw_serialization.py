#!/usr/bin/env python3
"""Check tb_cw_rom_serialize output against the MATLAB reference tables.

Reference: codeword = [hadamard(n); -hadamard(n)] rows in natural order,
serialized c0 first (ChirpSpreadSpectrum_Tx.m P/S converter).  The RTL ROM
must reproduce exactly this sequence for every reachable symbol.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import gen_golden_vectors as g


def main():
    dump = os.path.join(sys.argv[1] if len(sys.argv) > 1 else ".", "cw_serialized.txt")
    t4 = g.codeword_table(4)
    t32 = g.codeword_table(32)
    bad = 0
    n = 0
    for line in open(dump):
        f = line.split()
        rate, sym = int(f[0]), int(f[1])
        chips = [int(x) for x in f[2:]]
        ref = t4[sym] if rate == 0 else t32[sym]
        if chips != ref:
            print("FAIL rate=%d sym=%d\n  rtl %s\n  ref %s" % (rate, sym, chips, ref))
            bad += 1
        n += 1
    print("checked %d codewords, %d failures" % (n, bad))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
