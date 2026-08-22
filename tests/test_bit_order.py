#!/usr/bin/env python3
"""Directed bit-order regressions using intentionally asymmetric data."""
import sys
from pathlib import Path
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REFDIR = ROOT / "matlab" / "vector_generation"
sys.path.insert(0, str(REFDIR))
from css_reference import (
    RATE_1M, RATE_250K, payload_to_bits, framed_binary_data, demux_iq,
    serial_to_symbols, codeword_table, ppdu_iq_chips,
)
from test_architecture import controller_chips


class BitOrderTests(unittest.TestCase):
    def test_payload_bytes_are_lsb_first(self):
        cases = {
            0x01: [1,0,0,0,0,0,0,0],
            0x80: [0,0,0,0,0,0,0,1],
            0x96: [0,1,1,0,1,0,0,1],
            0xA5: [1,0,1,0,0,1,0,1],
            0x3C: [0,0,1,1,1,1,0,0],
        }
        for value, expected in cases.items():
            with self.subTest(value=f"0x{value:02X}"):
                self.assertEqual(payload_to_bits(bytes([value])).tolist(), expected)

    def test_phr_then_payload_boundary_keeps_order(self):
        framed = framed_binary_data(bytes([0x96]), RATE_1M)
        self.assertEqual(framed[12:20].tolist(), [0,1,1,0,1,0,0,1])

    def test_demux_on_asymmetric_payload_is_pairwise(self):
        framed = framed_binary_data(bytes([0x96, 0xA5]), RATE_1M)
        i_bits, q_bits = demux_iq(framed)
        for pair_index in range(len(framed)//2):
            self.assertEqual(i_bits[pair_index], framed[2*pair_index])
            self.assertEqual(q_bits[pair_index], framed[2*pair_index+1])

    def test_symbol_address_treats_first_serial_bit_as_msb(self):
        patterns = [([1,0,0], 4),([0,0,1], 1),([1,0,1], 5),([0,1,1], 3)]
        for bits, expected_symbol in patterns:
            got = serial_to_symbols(np.array(bits, dtype=np.int8), RATE_1M)
            self.assertEqual(int(got[0]), expected_symbol)

    def test_codeword_c0_is_first_transmitted_chip(self):
        table = codeword_table(RATE_1M)
        symbol = 5
        self.assertEqual(table[symbol].tolist(), [-1, 1, -1, 1])

    def test_controller_exactly_matches_reference_for_asymmetric_bytes(self):
        payloads = [bytes([0x01]), bytes([0x80]), bytes([0x96]), bytes([0xA5]), bytes([0x3C]), bytes([0x01,0x80,0x96,0xA5,0x3C])]
        for rate in (RATE_1M, RATE_250K):
            for payload in payloads:
                with self.subTest(rate=rate, payload=payload.hex()):
                    got_i, got_q = controller_chips(payload, rate)
                    exp_i, exp_q = ppdu_iq_chips(payload, rate)
                    np.testing.assert_array_equal(got_i, exp_i)
                    np.testing.assert_array_equal(got_q, exp_q)


if __name__ == "__main__":
    unittest.main(verbosity=2)
