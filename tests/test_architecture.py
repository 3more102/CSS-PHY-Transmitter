#!/usr/bin/env python3
"""Independent executable checks of the intended RTL architecture sequencing.

This deliberately reconstructs the controller's pairwise framing and the integer
QPSK/DQPSK/CSK datapath using generated ROM files. It is not an HDL simulator;
it is a cross-check that the selected streaming architecture is equivalent to
the supplied-MATLAB-derived reference before RTL simulation is available.
"""
import sys
from pathlib import Path
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REFDIR = ROOT / "matlab" / "vector_generation"
sys.path.insert(0, str(REFDIR))
from css_reference import (
    RATE_1M, RATE_250K, SFD, PREAMBLE_LENGTH, INTERLEAVER_PERM,
    phr_bits, padding_count, deterministic_payload, ppdu_iq_chips, transmit,
    gap_samples,
)


def load_codewords(rate: int):
    path = ROOT / "rtl" / "rom" / ("codeword_1m.mem" if rate == RATE_1M else "codeword_250k.mem")
    return [[1 if c == "1" else -1 for c in line.strip()] for line in path.read_text().splitlines() if line.strip()]


def load_chirp(m: int):
    def signed6(s: str) -> int:
        v = int(s, 2)
        return v - 64 if v & 0x20 else v
    rr = [signed6(x.strip()) for x in (ROOT / "rtl" / "rom" / f"chirp_m{m}_real.mem").read_text().splitlines()]
    ii = [signed6(x.strip()) for x in (ROOT / "rtl" / "rom" / f"chirp_m{m}_imag.mem").read_text().splitlines()]
    return np.array(rr, dtype=np.int16) + 1j * np.array(ii, dtype=np.int16)


def controller_chips(payload: bytes, rate: int):
    """Model css_tx_controller's pairwise hardware sequencing directly."""
    plen = len(payload)
    phr = phr_bits(plen).tolist()
    total_bits = 12 + 8 * plen + padding_count(plen, rate)
    total_pairs = total_bits // 2
    pairs = []
    for pair_idx in range(total_pairs):
        if pair_idx < 6:
            pi, pq = phr[2 * pair_idx], phr[2 * pair_idx + 1]
        elif pair_idx < 6 + 4 * plen:
            p = pair_idx - 6
            byte = payload[p >> 2]
            b = (p & 3) << 1
            pi, pq = (byte >> b) & 1, (byte >> (b + 1)) & 1
        else:
            pi = pq = 0
        pairs.append((pi, pq))

    table = load_codewords(rate)
    i_data, q_data = [], []
    width = 3 if rate == RATE_1M else 6
    block_pairs = width if rate == RATE_1M else 2 * width
    for base in range(0, len(pairs), block_pairs):
        if rate == RATE_1M:
            block = pairs[base:base + 3]
            ai = sum(bit << (2-j) for j, (bit, _) in enumerate(block))
            aq = sum(bit << (2-j) for j, (_, bit) in enumerate(block))
            i_data.extend(table[ai]); q_data.extend(table[aq])
        else:
            a = pairs[base:base + 6]
            b = pairs[base + 6:base + 12]
            ai = sum(bit << (5-j) for j, (bit, _) in enumerate(a))
            aq = sum(bit << (5-j) for j, (_, bit) in enumerate(a))
            bi = sum(bit << (5-j) for j, (bit, _) in enumerate(b))
            bq = sum(bit << (5-j) for j, (_, bit) in enumerate(b))
            raw_i = table[ai] + table[bi]
            raw_q = table[aq] + table[bq]
            i_data.extend([raw_i[int(k)] for k in INTERLEAVER_PERM])
            q_data.extend([raw_q[int(k)] for k in INTERLEAVER_PERM])

    sync = [1] * PREAMBLE_LENGTH[rate] + SFD[rate].astype(int).tolist()
    return np.array(sync + i_data, dtype=np.int8), np.array(sync + q_data, dtype=np.int8)


def integer_pipeline(payload: bytes, rate: int, chirp_index: int):
    ci, cq = controller_chips(payload, rate)
    qpsk = np.empty(len(ci), dtype=np.complex128)
    for n, (i, q) in enumerate(zip(ci, cq)):
        if i == 1 and q == 1: qpsk[n] = 1
        elif i == 1 and q == -1: qpsk[n] = -1j
        elif i == -1 and q == 1: qpsk[n] = 1j
        else: qpsk[n] = -1

    feedback = [1 + 1j] * 4
    dq = []
    for n, x in enumerate(qpsk):
        phase = n & 3
        y = x * feedback[phase]
        y = complex(int(y.real), int(y.imag))
        dq.append(y)
        feedback[phase] = y

    chirp = load_chirp(chirp_index)
    samples = []
    for g in range(0, len(dq), 4):
        syms = dq[g:g+4]
        for k in range(4):
            for v in chirp[k*38:(k+1)*38]:
                y = v * syms[k]
                samples.append(complex(int(y.real), int(y.imag)))
        samples.extend([0j] * gap_samples(chirp_index, bool((g // 4) & 1)))
    return np.array(samples, dtype=np.complex128)


class ArchitectureTests(unittest.TestCase):
    def test_controller_matches_reference_chip_stream(self):
        for rate in (RATE_1M, RATE_250K):
            for length in (0, 1, 3, 25, 127):
                payload = deterministic_payload(length)
                got_i, got_q = controller_chips(payload, rate)
                exp_i, exp_q = ppdu_iq_chips(payload, rate)
                np.testing.assert_array_equal(got_i, exp_i)
                np.testing.assert_array_equal(got_q, exp_q)

    def test_integer_architecture_matches_reference_samples(self):
        for rate in (RATE_1M, RATE_250K):
            for length in (0, 1, 3, 25, 127):
                payload = deterministic_payload(length)
                got = integer_pipeline(payload, rate, 1)
                exp = transmit(payload, rate, 1).samples
                np.testing.assert_array_equal(got, exp)

    def test_required_payload_matrix_matches_for_all_four_chirp_indices(self):
        for rate in (RATE_1M, RATE_250K):
            for length in (0, 1, 3, 25, 127):
                payload = deterministic_payload(length)
                for m in (1, 2, 3, 4):
                    with self.subTest(rate=rate, length=length, chirp=m):
                        got = integer_pipeline(payload, rate, m)
                        exp = transmit(payload, rate, m).samples
                        np.testing.assert_array_equal(got, exp)

    def test_all_four_chirp_indices_integer_output_fits_signed8(self):
        payload = deterministic_payload(3)
        for m in (1, 2, 3, 4):
            got = integer_pipeline(payload, RATE_1M, m)
            self.assertGreaterEqual(int(got.real.min()), -128)
            self.assertLessEqual(int(got.real.max()), 127)
            self.assertGreaterEqual(int(got.imag.min()), -128)
            self.assertLessEqual(int(got.imag.max()), 127)
            np.testing.assert_array_equal(got, transmit(payload, RATE_1M, m).samples)


if __name__ == "__main__":
    unittest.main(verbosity=2)
