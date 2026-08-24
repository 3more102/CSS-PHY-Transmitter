#!/usr/bin/env python3
"""CSS PHY transmitter golden vector generator.

Bit-accurate Python replica of the MATLAB fixed-point reference model in
matlab/original/CSS_PHY_Trasmitter-Floating-Fixed Point.  Generates:
  vectors/chirp_rom.hex   4 chirp-index banks x 4 subchirps x 38 samples, {re[5:0],im[5:0]}
  vectors/cw4.hex         8 codewords  x  4 chips (1 Mb/s bi-orthogonal table)
  vectors/cw32.hex        512 codewords x 32 chips (250 kb/s bi-orthogonal table)
  vectors/payload_*.hex   deterministic payload stimulus bytes
  vectors/golden_*.hex    expected TX sample stream, one "II QQ" hex pair per sample
"""
import cmath
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VEC = os.path.join(ROOT, "vectors")

FS = 32.0          # sampling frequency MHz
TSUB = 38          # subchirp length in samples
TCHIRP = 192       # chirp symbol length in samples
DAC_BITS = 6
DAC_MAX = 2 ** (DAC_BITS - 1) - 1      # 31
MU_MHZ = 7.3158
TAU_SAMPLES = [15, 10, 5, 0]           # Tau_m for chirp index m=1..4
PREAMBLE_LEN = [32, 80]
SFD = [
    [-1, 1, 1, 1, -1, 1, -1, -1, 1, -1, -1, 1, 1, 1, -1, -1],   # 1 Mb/s
    [-1, 1, 1, 1, 1, -1, 1, -1, -1, -1, 1, -1, -1, -1, 1, 1],   # 250 kb/s
]
PHR_LEN = 12


def raised_cosine():
    """raisedCosineGen(Tsub) for Tsub=38."""
    n_ones = 1 + math.floor(0.3 * TSUB)          # 12
    num_roll = TSUB // 2 - n_ones                # 7
    tmp = [1.0] * n_ones
    for n in range(n_ones, n_ones + num_roll + 1):   # n = [12..19] -> 8 samples
        tmp.append(0.5 * (1 + math.cos(5 * math.pi / TSUB * (n - 0.3 * TSUB))))
    rc = list(reversed(tmp)) + tmp[1:TSUB // 2]      # [fliplr(tmp), tmp(2:19)]
    assert len(rc) == TSUB, len(rc)
    return rc


def chirp_sequence(m):
    """chirpSequenceGenerator(m): returns 4 lists of TSUB complex samples."""
    zeta = [[1, 1, -1, -1],
            [1, -1, 1, -1],
            [-1, -1, 1, 1],
            [-1, 1, -1, 1]]
    fkm = [[-3.15, 3.15, 3.15, -3.15],
           [3.15, -3.15, -3.15, 3.15],
           [-3.15, 3.15, 3.15, -3.15],
           [3.15, -3.15, -3.15, 3.15]]
    rc = raised_cosine()
    seqs = []
    for k in range(4):
        col = []
        for t in range(-TSUB // 2, TSUB // 2):
            phase_arg = fkm[m - 1][k] + MU_MHZ * zeta[m - 1][k] / 2 / FS * t
            col.append(cmath.exp(2j * math.pi / FS * phase_arg * t) * rc[t + TSUB // 2])
        seqs.append(col)
    return seqs


def quantize(seqs):
    """floor(sample * (2^(TxDACbitNumber-1)-1)) per runMe.m fixed-point step."""
    out = []
    for col in seqs:
        out.append([(int(math.floor(s.real * DAC_MAX)), int(math.floor(s.imag * DAC_MAX)))
                    for s in col])
    return out


def hadamard(n):
    h = [[1]]
    while len(h) < n:
        h = [row + row for row in h] + [row + [-x for x in row] for row in h]
    return h


def codeword_table(n):
    """Bi-orthogonal table as 0/1 chip bits: first hadamard(n) rows, then negated."""
    std = hadamard(n)
    return [[(x + 1) // 2 for x in row] for row in std] + \
           [[(-x + 1) // 2 for x in row] for row in std]


def build_phr_bits(payload_len):
    """PHR exactly as ChirpSpreadSpectrum_Tx.m builds it (LSB transmitted first)."""
    msb_first = [(payload_len >> (6 - i)) & 1 for i in range(7)]  # dec2bin(len,7)
    lsb_first = list(reversed(msb_first))                          # payloadLength_Binary(7:-1:1)=...
    return lsb_first + [0, 0] + [0, 0, 0]


def padding_by(rate, payload_len_bytes):
    """Reference quirk: result is never zero (min 1 bit of padding)."""
    total = PHR_LEN + 8 * payload_len_bytes
    if rate == 0:
        return 6 - (total % 6)
    return 24 - (total % 24)


def tx_chips(payload_len, rate, case_seed=0):
    pad = padding_by(rate, payload_len)
    """Chip-level I/Q stream (+1/-1) before QPSK mapping."""
    pre_len = PREAMBLE_LEN[rate]
    cw_len = 4 if rate == 0 else 32
    bits_per_cw = 3 if rate == 0 else 6
    table = codeword_table(cw_len)

    data_bits = build_phr_bits(payload_len)
    payload = payload_stimulus(payload_len, seed=case_seed)
    for byte in payload:
        data_bits += [(byte >> (7 - i)) & 1 for i in range(8)]
    data_bits += [0] * pad

    i_path = data_bits[0::2]
    q_path = data_bits[1::2]
    num_cw = len(i_path) // bits_per_cw
    assert len(i_path) == num_cw * bits_per_cw

    def to_dec(bits):
        v = 0
        for b in bits:              # first bit is MSB (binary2decimal.m)
            v = (v << 1) | b
        return v

    i_syms = [to_dec(i_path[n * bits_per_cw:(n + 1) * bits_per_cw]) for n in range(num_cw)]
    q_syms = [to_dec(q_path[n * bits_per_cw:(n + 1) * bits_per_cw]) for n in range(num_cw)]

    def serialize(syms):
        words = [table[s] for s in syms]         # chip c0 .. c{n-1}, value 0/1
        if rate == 1:
            out = []
            for b in range(0, len(words), 2):
                combined = words[b] + words[b + 1]        # 64 entries, idx 0..63
                out.append([combined[idx] for idx in INTERLEAVER_IDX])
            return [c for w in out for c in w]
        return [c for w in words for c in w]

    i_stream = serialize(i_syms)
    q_stream = serialize(q_syms)

    pre = [1] * pre_len
    sfd = [(s + 1) // 2 for s in SFD[rate]]
    chips_i = pre + sfd + i_stream
    chips_q = pre + sfd + q_stream
    return chips_i, chips_q


INTERLEAVER_IDX = [0, 1, 2, 3, 52, 53, 54, 55, 8, 9, 10, 11, 60, 61, 62, 63,
                   16, 17, 18, 19, 36, 37, 38, 39, 24, 25, 26, 27, 44, 45, 46, 47,
                   32, 33, 34, 35, 20, 21, 22, 23, 40, 41, 42, 43, 28, 29, 30, 31,
                   48, 49, 50, 51, 4, 5, 6, 7, 56, 57, 58, 59, 12, 13, 14, 15]


def dqpsk_modulate(chips_i, chips_q, chirp_q, m):
    """DQPSK encode + DQCSK modulation incl. gaps. Returns (re_list, im_list)."""
    gap_lo = TCHIRP - 4 * TSUB - 2 * TAU_SAMPLES[m - 1]
    gap_hi = TCHIRP - 4 * TSUB + 2 * TAU_SAMPLES[m - 1]

    # lane accumulators (units of 45 deg), start phase exp(j*pi/4) => unit 1
    cum = [0, 0, 0, 0]
    re_out, im_out = [], []
    group = 0
    for base in range(0, len(chips_i), 4):
        for k in range(4):
            ci, cq = chips_i[base + k], chips_q[base + k]
            # ((I+Q) - j(I-Q))/2 -> step in units of 90 deg (x2 => 45-deg units)
            step = {(1, 1): 0, (0, 1): 2, (1, 0): -2, (0, 0): 4}[(ci, cq)]
            cum[k] = (cum[k] + step) % 8
            u = (1 + cum[k]) % 8
            a = round(math.cos(u * math.pi / 4))
            b = round(math.sin(u * math.pi / 4))
            for (sr, si) in chirp_q[k]:
                re_out.append(a * sr - b * si)
                im_out.append(b * sr + a * si)
        gap = gap_lo if group % 2 == 0 else gap_hi
        re_out += [0] * gap
        im_out += [0] * gap
        group += 1
    return re_out, im_out


# ---------------------------------------------------------------- stimulus --
_state = 0x2B


def _rand_byte():
    global _state
    for _ in range(8):
        bit = ((_state >> 15) ^ (_state >> 13) ^ (_state >> 12) ^ (_state >> 10)) & 1
        _state = ((_state << 1) | bit) & 0xFFFF
    return _state & 0xFF


def payload_stimulus(length, seed=0):
    global _state
    _state = 0x2B + seed * 7919
    _rand_byte()
    return [_rand_byte() for _ in range(length)]


# ------------------------------------------------------------------- output --
def twos(value, width):
    return value & ((1 << width) - 1)


def main():
    os.makedirs(VEC, exist_ok=True)

    # chirp ROM: bank per chirp index m=1..4, word = {re[5:0], im[5:0]}
    with open(os.path.join(VEC, "chirp_rom.hex"), "w") as f:
        for m in range(1, 5):
            for (r, i) in [q for col in quantize(chirp_sequence(m)) for q in col]:
                f.write("%02x%02x\n" % (twos(r, 6), twos(i, 6)))

    with open(os.path.join(VEC, "cw4.hex"), "w") as f:
        for row in codeword_table(4):
            f.write("%x\n" % int("".join(str(b) for b in row), 2))

    with open(os.path.join(VEC, "cw32.hex"), "w") as f:
        for row in codeword_table(32):
            f.write("%08x\n" % int("".join(str(b) for b in row), 2))

    cases = [
        (0, 20, 1), (0, 55, 1), (0, 127, 1),
        (1, 20, 1), (1, 55, 1), (1, 127, 1),
        (0, 25, 2), (1, 40, 4),
    ]
    manifest = []
    for case_id, (rate, length, m) in enumerate(cases):
        tag = "rate%d_len%d_m%d" % (rate, length, m)

        plen = length
        payload = payload_stimulus(length, seed=case_id)
        with open(os.path.join(VEC, "payload_%s.hex" % tag), "w") as f:
            for byte in payload:
                f.write("%02x\n" % byte)

        ci, cq = tx_chips(length, rate, case_seed=case_id)
        chirp_q = quantize(chirp_sequence(m))
        re_s, im_s = dqpsk_modulate(ci, cq, chirp_q, m)
        with open(os.path.join(VEC, "golden_%s.hex" % tag), "w") as f:
            for r, i in zip(re_s, im_s):
                f.write("%02x%02x\n" % (twos(r, 8), twos(i, 8)))
        manifest.append((tag, rate, length, m, len(re_s)))
        print("%-18s samples=%d pad=%d" % (tag, len(re_s), padding_by(rate, length)))

    with open(os.path.join(VEC, "manifest.txt"), "w") as f:
        for tag, rate, length, m, nsamp in manifest:
            f.write("%s %d %d %d %d\n" % (tag, rate, length, m, nsamp))
    print("done: %d golden cases" % len(manifest))


if __name__ == "__main__":
    main()
