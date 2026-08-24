"""Cross-check gen_golden_vectors primitives against MATLAB reference dumps."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_golden_vectors import (VEC, chirp_sequence, quantize, codeword_table,
                                build_phr_bits, raised_cosine, SFD)

MAT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "matlab", "original",
                   "CSS_PHY_Trasmitter-Floating-Fixed Point")


def to_signed(v, w):
    return v - (1 << w) if v >= (1 << (w - 1)) else v


def check_chirp_rom():
    re_ref = [int(l.strip(), 2) for l in open(os.path.join(MAT, "chirpSequenceReal_tofile.txt")) if l.strip()]
    im_ref = [int(l.strip(), 2) for l in open(os.path.join(MAT, "chirpSequenceImag_tofile.txt")) if l.strip()]
    assert len(re_ref) == 152 and len(im_ref) == 152
    q = quantize(chirp_sequence(1))
    flat = [s for col in q for s in col]   # column-major: subchirp k blocks of 38
    bad = 0
    for n, ((r, i), rr, ii) in enumerate(zip(flat, re_ref, im_ref)):
        rr, ii = to_signed(rr, 6), to_signed(ii, 6)
        if r != rr or i != ii:
            bad += 1
            if bad <= 5:
                print("  mismatch n=%d py=(%d,%d) matlab=(%d,%d)" % (n, r, i, rr, ii))
    print("chirp ROM vs MATLAB dump: %d/%d samples match" % (152 - bad, 152))
    return bad == 0


def check_codewords():
    ref = [[int(c) for c in l.strip()] for l in open(os.path.join(MAT, "codeword_1Mbs.txt")) if l.strip()]
    mine = codeword_table(4)
    if mine != ref:
        print("codeword table 4 MISMATCH")
        return False
    print("codeword table  4: %d rows match" % len(ref))
    return True


def check_sfd():
    bits = [int(c) for l in open(os.path.join(MAT, "preambleSFD.txt")) if l.strip()
            for c in l.strip()]
    pre = bits[:32]
    sfd = [b * 2 - 1 for b in bits[32:48]]
    ok_pre = len(pre) == 32 and all(b == 1 for b in pre)
    sfd_ref = [(s + 1) // 2 for s in SFD[0]]
    print("preamble 32 chips all ones: %s" % ok_pre)
    print("SFD 1Mb/s match: %s (%s)" % (bits[32:48] == sfd_ref, sfd_ref))
    return ok_pre and bits[32:48] == sfd_ref


def check_hadamard32():
    """codeword_250kbs.txt is a mangled fprintf dump (4 values/line), so verify
    the 32-chip table structurally instead: Sylvester hadamard + negations."""
    from gen_golden_vectors import codeword_table
    tbl = codeword_table(32)
    top = [[2 * b - 1 for b in row] for row in tbl[:32]]
    bot = [[2 * b - 1 for b in row] for row in tbl[32:]]
    ok = all(bot[i] == [-x for x in top[i]] for i in range(32))
    # orthogonality of top half
    import itertools
    for a, b in itertools.combinations(range(32), 2):
        if sum(x * y for x, y in zip(top[a], top[b])) != 0:
            ok = False
            break
    # H32 = [H16 H16; H16 -H16]
    h16 = [[2 * b - 1 for b in row] for row in codeword_table(16)[:16]]
    blk_ok = all(top[i][:16] == h16[i] and top[i][16:] == h16[i] for i in range(16)) and \
             all(top[16 + i][:16] == h16[i] and top[16 + i][16:] == [-x for x in h16[i]]
                 for i in range(16))
    print("hadamard-32 table: negation=%s orthogonal=%s recursive=%s"
          % (all(bot[i] == [-x for x in top[i]] for i in range(32)), ok, blk_ok))
    return ok and blk_ok


def sanity_packet(rate, length):
    bits = build_phr_bits(length)
    print("rate=%d len=%d PHR bits(LSB-first): %s" % (rate, length, "".join(map(str, bits))))
    total = 12 + 8 * length
    cw = 3 if rate == 0 else 6
    pad = (cw * 2) - (total % (cw * 2))
    print("  data bits=%d pad=%d numCodeWords=%d chips=%d groups=%d samples=%d"
          % (total, pad, (total + pad) // (2 * cw), (total + pad) // 2,
             ((total + pad) // 2 + 3) // 4, (((total + pad) // 2 + 3) // 4) * 192))


if __name__ == "__main__":
    rc = check_chirp_rom() & check_codewords() & check_sfd() & check_hadamard32()
    sanity_packet(0, 20)
    sanity_packet(1, 55)
    sys.exit(0 if rc else 1)
