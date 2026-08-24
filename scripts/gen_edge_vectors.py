#!/usr/bin/env python3
"""Generate golden vectors for the edge-case regression.

Covers both data rates with payload lengths 0, 1, 3, the crossover
lengths (20/25) and the maximum 127 bytes -> 10 cases total.
Output goes to a scratch simulation directory (default sim_edge/):
  payload_<tag>.hex   deterministic stimulus bytes (seed = case_id)
  golden_<tag>.hex    expected TX sample stream
  manifest.txt        tag rate plen m nsamp case_id payload_crc

The ROM tables (chirp_rom.hex / cw4.hex / cw32.hex) are copied from
vectors/ so this directory is self-contained for vsim.
"""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import gen_golden_vectors as g

# (rate, plen, chirp_index m)
CASES = [
    (0, 0, 1), (0, 1, 1), (0, 3, 1), (0, 20, 1), (0, 127, 1),
    (1, 0, 1), (1, 1, 1), (1, 3, 1), (1, 25, 2), (1, 127, 1),
]


def crc16(data):
    crc = 0
    for b in data:
        crc = ((crc << 1) | (crc >> 15)) & 0xFFFF
        crc ^= b
        crc &= 0xFFFF
    return "%04x" % crc


def main():
    outdir = os.path.join(ROOT,
                          sys.argv[1] if len(sys.argv) > 1 else "sim_edge")
    os.makedirs(outdir, exist_ok=True)
    for name in ("chirp_rom.hex", "cw4.hex", "cw32.hex"):
        shutil.copyfile(os.path.join(g.VEC, name), os.path.join(outdir, name))

    manifest = []
    for case_id, (rate, plen, m) in enumerate(CASES):
        tag = "edge_rate%d_len%d" % (rate, plen)
        payload = g.payload_stimulus(plen, seed=case_id)

        with open(os.path.join(outdir, "payload_%s.hex" % tag), "w") as f:
            for byte in payload:
                f.write("%02x\n" % byte)
        stim = [int(l, 16) for l in
                open(os.path.join(outdir, "payload_%s.hex" % tag)).read().split()]
        assert stim == payload, "stimulus rewrite mismatch for %s" % tag

        ci, cq = g.tx_chips(plen, rate, case_seed=case_id)
        # guard against silent seed drift (same policy as the official
        # cases): some other nearby seed MUST produce a different chip
        # stream.  (case_id+1 itself may collide on short payloads because
        # the stimulus LFSR can emit the same first bytes.)
        if plen > 0:
            alt_ok = False
            for alt_seed in range(case_id + 1, case_id + 17):
                alt_i, _ = g.tx_chips(plen, rate, case_seed=alt_seed)
                if alt_i != ci:
                    alt_ok = True
                    break
            assert alt_ok, "seed drift guard failed for %s" % tag

        chirp_q = g.quantize(g.chirp_sequence(m))
        re_s, im_s = g.dqpsk_modulate(ci, cq, chirp_q, m)
        with open(os.path.join(outdir, "golden_%s.hex" % tag), "w") as f:
            for r, i in zip(re_s, im_s):
                f.write("%02x%02x\n" % (g.twos(r, 8), g.twos(i, 8)))

        manifest.append((tag, rate, plen, m, len(re_s), case_id, crc16(payload)))
        print("%-18s samples=%d pad=%d case_id=%d seed=%d payload_crc=%s"
              % (tag, len(re_s), g.padding_by(rate, plen), case_id,
                 case_id, crc16(payload)))

    with open(os.path.join(outdir, "manifest.txt"), "w") as f:
        for row in manifest:
            f.write("%s %d %d %d %d %d %s\n" % row)
    print("done: %d edge cases in %s" % (len(manifest), outdir))


if __name__ == "__main__":
    main()
