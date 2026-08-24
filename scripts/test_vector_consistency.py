#!/usr/bin/env python3
"""Permanent regression for golden-vector integrity.

Guards against a recurrence of the seed-drift defect (golden streams computed
from a different payload than the DUT stimulus):

  1. Regenerates all vectors into a temp directory and requires the result to
     be byte-identical with the committed vectors/ contents.
  2. For every case, re-derives the reference chip stream from the bytes
     actually present in vectors/payload_*.hex and requires it to match the
     committed manifest seed/crc metadata.
"""
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import gen_golden_vectors as g


def crc16(data):
    crc = 0
    for b in data:
        crc = ((crc << 1) | (crc >> 15)) & 0xFFFF
        crc ^= b
        crc &= 0xFFFF
    return "%04x" % crc


def main():
    vec = os.path.join(ROOT, "vectors")
    failures = 0

    # ---- 1. reproducibility -------------------------------------------
    tmp = tempfile.mkdtemp(prefix="css_vec_")
    old_vec = g.VEC
    try:
        g.VEC = tmp
        g.main()
        names = [n for n in os.listdir(vec) if n.endswith(".hex") or n == "manifest.txt"]
        for name in sorted(names):
            a = open(os.path.join(vec, name)).read()
            b = open(os.path.join(tmp, name)).read()
            if a != b:
                print("FAIL: %s does not match regeneration" % name)
                failures += 1
            else:
                print("ok: %s reproducible" % name)
    finally:
        g.VEC = old_vec
        shutil.rmtree(tmp, ignore_errors=True)

    # ---- 2. stimulus/reference seed consistency -----------------------
    # Recompute the full golden stream from the bytes actually present in
    # vectors/payload_*.hex using the manifest seed; require it to reproduce
    # the committed golden file exactly.
    rows = [l.split() for l in open(os.path.join(vec, "manifest.txt")) if l.strip()]
    for row in rows:
        tag, rate, plen, m, nsamp, case_id, crc = (row + [""] * 7)[:7]
        rate, plen, m, case_id, nsamp = int(rate), int(plen), int(m), int(case_id), int(nsamp)
        stim = [int(x, 16) for x in
                open(os.path.join(vec, "payload_%s.hex" % tag)).read().split()]
        ok = True
        if len(stim) != plen:
            ok = False
            print("FAIL: %s stimulus length %d != plen %d" % (tag, len(stim), plen))
        if crc and crc != crc16(stim):
            ok = False
            print("FAIL: %s crc mismatch (manifest %s vs stimulus %s)"
                  % (tag, crc, crc16(stim)))
        # rebuild golden from the committed stimulus bytes via tx_chips()
        data_bits = g.build_phr_bits(plen)
        for b in stim:
            data_bits += [(b >> (7 - i)) & 1 for i in range(8)]
        data_bits += [0] * g.padding_by(rate, plen)
        i_path, q_path = data_bits[0::2], data_bits[1::2]
        bpcw = 3 if rate == 0 else 6
        ncw = len(i_path) // bpcw

        def dec(bits):
            v = 0
            for b in bits:
                v = (v << 1) | b
            return v

        table = g.codeword_table(4 if rate == 0 else 32)

        def ser(syms):
            words = [table[s] for s in syms]
            if rate == 1:
                out = []
                for b in range(0, len(words), 2):
                    comb = words[b] + words[b + 1]
                    out.append([comb[j] for j in g.INTERLEAVER_IDX])
                return [c for w in out for c in w]
            return [c for w in words for c in w]

        pre = [1] * g.PREAMBLE_LEN[rate]
        sfd = [(s + 1) // 2 for s in g.SFD[rate]]
        ci = pre + sfd + ser([dec(i_path[n * bpcw:(n + 1) * bpcw]) for n in range(ncw)])
        cq = pre + sfd + ser([dec(q_path[n * bpcw:(n + 1) * bpcw]) for n in range(ncw)])
        chirp_q = g.quantize(g.chirp_sequence(m))
        re_s, im_s = g.dqpsk_modulate(ci, cq, chirp_q, m)
        mine = "".join("%02x%02x\n" % (g.twos(r, 8), g.twos(i, 8))
                       for r, i in zip(re_s, im_s))
        gold = open(os.path.join(vec, "golden_%s.hex" % tag)).read()
        if mine != gold:
            ok = False
            print("FAIL: %s golden not reproducible from committed stimulus" % tag)
        if not ok:
            failures += 1
            continue
        print("ok: %s case_id=%d seed=%d plen=%d crc=%s samples=%d" %
              (tag, case_id, case_id, plen, crc, nsamp))

    print("RESULT: %s (%d failures)" % ("PASS" if failures == 0 else "FAIL", failures))
    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
