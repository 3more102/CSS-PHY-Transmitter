#!/usr/bin/env python3
"""Deterministic randomized architecture/reference equivalence regression."""
import random
import sys
from pathlib import Path
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REFDIR = ROOT / "matlab" / "vector_generation"
sys.path.insert(0, str(REFDIR))
from css_reference import RATE_1M, RATE_250K, ppdu_iq_chips, transmit
from test_architecture import controller_chips, integer_pipeline

SEED = 0x802154


def cases_for_rate(rate: int):
    rng = random.Random(SEED ^ (rate << 20))
    lengths = [2, 4, 7, 11, 31, 64, 95, 126]
    for length in lengths:
        payload = bytes(rng.randrange(256) for _ in range(length))
        chirp_index = 1 + rng.randrange(4)
        yield length, payload, chirp_index


class RandomizedEquivalenceTests(unittest.TestCase):
    def test_fixed_seed_is_recorded(self):
        self.assertEqual(SEED, 0x802154)

    def test_randomized_controller_chip_equivalence(self):
        for rate in (RATE_1M, RATE_250K):
            for length, payload, _ in cases_for_rate(rate):
                with self.subTest(seed=hex(SEED), rate=rate, length=length):
                    got_i, got_q = controller_chips(payload, rate)
                    exp_i, exp_q = ppdu_iq_chips(payload, rate)
                    np.testing.assert_array_equal(got_i, exp_i)
                    np.testing.assert_array_equal(got_q, exp_q)

    def test_randomized_full_integer_pipeline_equivalence(self):
        for rate in (RATE_1M, RATE_250K):
            for length, payload, chirp_index in cases_for_rate(rate):
                with self.subTest(seed=hex(SEED), rate=rate, length=length, chirp=chirp_index):
                    got = integer_pipeline(payload, rate, chirp_index)
                    exp = transmit(payload, rate, chirp_index).samples
                    np.testing.assert_array_equal(got, exp)
                    self.assertGreaterEqual(int(got.real.min()), -128)
                    self.assertLessEqual(int(got.real.max()), 127)
                    self.assertGreaterEqual(int(got.imag.min()), -128)
                    self.assertLessEqual(int(got.imag.max()), 127)


if __name__ == "__main__":
    unittest.main(verbosity=2)
