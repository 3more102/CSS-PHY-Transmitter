#!/usr/bin/env python3
import sys
from pathlib import Path
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REFDIR = ROOT / "matlab" / "vector_generation"
ORIG = ROOT / "matlab" / "original"
sys.path.insert(0, str(REFDIR))
from css_reference import *


def signed_bin(s: str) -> int:
    s = s.strip()
    v = int(s, 2)
    if v & (1 << (len(s)-1)):
        v -= 1 << len(s)
    return v


class ReferenceTests(unittest.TestCase):
    def test_mapper_1m_matches_supplied_file(self):
        source = [line.strip() for line in (ORIG / "codeword_1Mbs.txt").read_text().splitlines() if line.strip()]
        generated = ["".join("1" if x == 1 else "0" for x in row) for row in codeword_table(RATE_1M)]
        self.assertEqual(source, generated)

    def test_mapper_250k_matches_supplied_file(self):
        chunks = [line.strip() for line in (ORIG / "codeword_250kbs.txt").read_text().splitlines() if line.strip()]
        self.assertEqual(len(chunks), 512)
        source = ["".join(chunks[i:i+8]) for i in range(0, 512, 8)]
        generated = ["".join("1" if x == 1 else "0" for x in row) for row in codeword_table(RATE_250K)]
        self.assertEqual(source, generated)

    def test_chirp_m1_exactly_matches_supplied_fixed_vectors(self):
        source_r = np.array([signed_bin(x) for x in (ORIG / "chirpSequenceReal_tofile.txt").read_text().splitlines()])
        source_i = np.array([signed_bin(x) for x in (ORIG / "chirpSequenceImag_tofile.txt").read_text().splitlines()])
        generated = chirp_sequence_fixed(1).reshape(-1, order="F")
        np.testing.assert_array_equal(source_r, generated.real.astype(int))
        np.testing.assert_array_equal(source_i, generated.imag.astype(int))


    def test_all_four_chirp_roms_match_reference_equations(self):
        def read_signed6(path):
            values=[]
            for raw in path.read_text().splitlines():
                raw=raw.strip()
                if not raw:
                    continue
                value=int(raw,2)
                if value & 0x20:
                    value-=64
                values.append(value)
            return np.array(values,dtype=int)
        for m in range(1,5):
            expected=chirp_sequence_fixed(m).reshape(-1,order="F")
            got_r=read_signed6(ROOT/"rtl"/"rom"/f"chirp_m{m}_real.mem")
            got_i=read_signed6(ROOT/"rtl"/"rom"/f"chirp_m{m}_imag.mem")
            np.testing.assert_array_equal(got_r,expected.real.astype(int))
            np.testing.assert_array_equal(got_i,expected.imag.astype(int))

    def test_every_payload_length_is_four_symbol_group_aligned(self):
        for rate in (RATE_1M,RATE_250K):
            for length in range(128):
                payload=bytes(length)
                result=transmit(payload,rate,1)
                self.assertEqual(len(result.dqpsk)%4,0,(rate,length))

    def test_phr_is_lsb_first(self):
        bits = phr_bits(25)
        self.assertEqual(bits.tolist(), [1,0,0,1,1,0,0,0,0,0,0,0])
        # The supplied payload export reverses each byte for text output; its
        # first line therefore must equal the first 8 PHR bits reversed.
        first_line = (ORIG / "payload.txt").read_text().splitlines()[0].strip()
        self.assertEqual(first_line, "".join(str(x) for x in bits[:8][::-1]))

    def test_matlab_padding_full_block_behavior_is_preserved(self):
        self.assertEqual(padding_count(3, RATE_1M), 6)  # 12+24 is already divisible by 6
        self.assertEqual(len(framed_binary_data(bytes(3), RATE_1M)), 42)

    def test_demux_first_bit_goes_to_i(self):
        bits = np.array([1,0,0,1,1,1], dtype=np.int8)
        i, q = demux_iq(bits)
        self.assertEqual(i.tolist(), [1,0,1])
        self.assertEqual(q.tolist(), [0,1,1])

    def test_symbol_address_first_bit_is_msb(self):
        bits = np.array([1,0,1, 0,1,1], dtype=np.int8)
        self.assertEqual(serial_to_symbols(bits, RATE_1M).tolist(), [5,3])

    def test_interleaver_permutation(self):
        words = np.vstack([np.arange(32), np.arange(32,64)])
        out = interleave_250k(words).reshape(-1)
        np.testing.assert_array_equal(out, INTERLEAVER_PERM)

    def test_qpsk_mapping_matches_matlab_equation(self):
        i = np.array([1,1,-1,-1])
        q = np.array([1,-1,1,-1])
        y = qpsk_map(i,q)
        np.testing.assert_array_equal(y, np.array([1, -1j, 1j, -1]))

    def test_dqpsk_feedback_length_four(self):
        x = np.array([1,1,1,1, -1j,-1j,-1j,-1j], dtype=complex)
        y = dqpsk_encode(x)
        np.testing.assert_array_equal(y[:4], np.array([1+1j]*4))
        np.testing.assert_array_equal(y[4:8], np.array([1-1j]*4))

    def test_gap_table(self):
        expected = [(10,70),(20,60),(30,50),(40,40)]
        for m,(even,odd) in enumerate(expected,1):
            self.assertEqual(gap_samples(m,False), even)
            self.assertEqual(gap_samples(m,True), odd)

    def test_mse_floor_requires_at_least_five_bits_for_threshold(self):
        self.assertGreater(chirp_mse(1,4,"floor"), 0.005)
        self.assertLess(chirp_mse(1,5,"floor"), 0.005)
        self.assertLess(chirp_mse(1,6,"floor"), 0.005)

    def test_reference_rounding_r4_discrepancy_is_reproducible(self):
        self.assertLess(chirp_mse(1,4,"round"), 0.005)

    def test_full_chain_symbol_count_is_group_aligned(self):
        for rate in (RATE_1M, RATE_250K):
            for length in (0,1,25,127):
                payload = deterministic_payload(length)
                result = transmit(payload, rate, 1)
                self.assertEqual(len(result.dqpsk) % 4, 0)
                self.assertEqual(len(result.i_chips), len(result.q_chips))


if __name__ == "__main__":
    unittest.main(verbosity=2)
