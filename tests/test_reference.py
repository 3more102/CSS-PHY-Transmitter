#!/usr/bin/env python3
import sys
from pathlib import Path
import math
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

    # ------------------------------------------------------------------
    # Numerical verification additions (reference worker): each check is
    # pinned against matlab/original ground truth or the documented
    # MATLAB formulas, never against RTL behavior.
    # ------------------------------------------------------------------

    REPORTS = ROOT / "reports"

    @staticmethod
    def _read_csv_rows(path: Path):
        lines = [l.strip() for l in path.read_text().splitlines() if l.strip()]
        header = lines[0].split(",")
        return [dict(zip(header, l.split(","))) for l in lines[1:]]

    def test_mse_contract_six_bits_passes_for_every_chirp(self):
        for m in range(1, 5):
            mse = chirp_mse(m, TX_DAC_BITS, "floor")
            self.assertLess(
                mse, 0.005,
                f"6-bit floor MSE {mse} violates contract for chirp m={m}")

    def test_mse_report_csvs_match_live_recomputation(self):
        results_path = self.REPORTS / "mse_results.csv"
        all_path = self.REPORTS / "mse_all_chirps.csv"
        if not results_path.exists():
            self.skipTest("reports/mse_results.csv not generated yet")
        for row in self._read_csv_rows(results_path):
            bits = int(row["bits"])
            with self.subTest(bits=bits):
                live_round = chirp_mse(1, bits, "round")
                live_floor = chirp_mse(1, bits, "floor")
                self.assertAlmostEqual(float(row["round_mse"]), live_round, delta=abs(live_round)*1e-9+1e-15)
                self.assertAlmostEqual(float(row["floor_mse"]), live_floor, delta=abs(live_floor)*1e-9+1e-15)
                self.assertEqual(row["floor_pass_0p005"], str(live_floor < 0.005).lower())
                self.assertEqual(row["round_pass_0p005"], str(live_round < 0.005).lower())
        if not all_path.exists():
            self.skipTest("reports/mse_all_chirps.csv not generated yet")
        for row in self._read_csv_rows(all_path):
            m, bits = int(row["chirp_index"]), int(row["bits"])
            with self.subTest(chirp=m, bits=bits):
                live = chirp_mse(m, bits, "floor")
                self.assertAlmostEqual(float(row["floor_mse"]), live, delta=abs(live)*1e-9+1e-15)
                self.assertEqual(row["pass_0p005"], str(live < 0.005).lower())

    def test_chirp_rom_m1_matches_supplied_text_directly(self):
        """Independent chain: committed ROM bytes vs original text vectors,
        deliberately without css_reference in between."""
        def read_signed_text(path):
            out = []
            for raw in path.read_text().splitlines():
                raw = raw.strip()
                if not raw:
                    continue
                v = int(raw, 2)
                out.append(v - (1 << len(raw)) if v & (1 << (len(raw)-1)) else v)
            return out
        def read_mem(path):
            out = []
            for raw in path.read_text().splitlines():
                raw = raw.strip()
                if not raw:
                    continue
                v = int(raw, 2)
                out.append(v - 64 if v & 0x20 else v)
            return out
        for comp in ("real", "imag"):
            src = read_signed_text(ORIG / f"chirpSequence{comp.capitalize()}_tofile.txt")
            rom = read_mem(ROOT / "rtl" / "rom" / f"chirp_m1_{comp}.mem")
            self.assertEqual(len(src), 152)
            self.assertEqual(src, rom, f"chirp_m1_{comp}.mem diverges from supplied text")

    def test_codeword_roms_match_supplied_text_files_byte_for_byte(self):
        mem_1m = [l.strip() for l in (ROOT/"rtl"/"rom"/"codeword_1m.mem").read_text().splitlines() if l.strip()]
        txt_1m = [l.strip() for l in (ORIG / "codeword_1Mbs.txt").read_text().splitlines() if l.strip()]
        self.assertEqual(txt_1m, mem_1m)
        chunks = [l.strip() for l in (ORIG / "codeword_250kbs.txt").read_text().splitlines() if l.strip()]
        words_from_txt = ["".join(chunks[i:i+8]) for i in range(0, len(chunks), 8)]
        mem_250k = [l.strip() for l in (ROOT/"rtl"/"rom"/"codeword_250k.mem").read_text().splitlines() if l.strip()]
        self.assertEqual(words_from_txt, mem_250k)

    def test_four_chirp_sequences_are_pairwise_distinct(self):
        seqs = {m: chirp_sequence_float(m) for m in range(1, 5)}
        for a in range(1, 5):
            for b in range(a+1, 5):
                with self.subTest(pair=(a, b)):
                    self.assertGreater(float(np.max(np.abs(seqs[a]-seqs[b]))), 1.5,
                        "chirp table columns collapsed; per-index math is degenerate")

    def test_mse_symmetry_across_chirps_as_documented(self):
        mses = [chirp_mse(m, TX_DAC_BITS, "floor") for m in range(1, 5)]
        self.assertLess(max(mses) - min(mses), 1e-12)

    def test_padding_follows_matlab_formula_for_every_length_and_rate(self):
        for rate in (RATE_1M, RATE_250K):
            n = PAD_MODULUS[rate]
            for length in range(128):
                expected = n - ((8*length + PHR_LENGTH) % n)
                self.assertEqual(padding_count(length, rate), expected,
                                 f"L={length} rate={rate}")
        # The MATLAB quirk: exact multiples still receive a full pad block.
        self.assertEqual(padding_count(0, RATE_1M), 6)
        self.assertEqual(padding_count(0, RATE_250K), 12)

    def test_payload_length_sweep_structural_invariants(self):
        for rate in (RATE_1M, RATE_250K):
            sym_bits = BITS_PER_SYMBOL[rate]
            cw_len = CODEWORD_LENGTH[rate]
            sync_len = PREAMBLE_LENGTH[rate] + SFD_LENGTH
            for length in range(128):
                payload = deterministic_payload(length)
                framed = framed_binary_data(payload, rate)
                with self.subTest(rate=rate, length=length):
                    self.assertEqual(len(framed), 12 + 8*length + padding_count(length, rate))
                    self.assertEqual(len(framed) % (2*sym_bits), 0)
                    result = transmit(payload, rate, 1)
                    expected_chips = sync_len + (len(framed)//2 // sym_bits) * cw_len
                    self.assertEqual(len(result.i_chips), expected_chips)
                    self.assertEqual(len(result.q_chips), expected_chips)
                    groups = len(result.dqpsk) // 4
                    expected_samples = sum(
                        152 + gap_samples(1, bool(g & 1)) for g in range(groups))
                    self.assertEqual(len(result.samples), expected_samples)

    def test_tx_samples_fit_signed8_across_length_sweep(self):
        lo, hi = 127, -128
        for rate in (RATE_1M, RATE_250K):
            for length in range(128):
                samples = transmit(deterministic_payload(length), rate, 1).samples
                lo = min(lo, int(samples.real.min()), int(samples.imag.min()))
                hi = max(hi, int(samples.real.max()), int(samples.imag.max()))
        self.assertGreaterEqual(lo, -128)
        self.assertLessEqual(hi, 127)

    def test_qpsk_exhaustive_alphabet_and_dqpsk_constant_magnitude(self):
        combos = [(i, q) for i in (-1, 1) for q in (-1, 1)]
        y = qpsk_map(np.array([c[0] for c in combos]),
                     np.array([c[1] for c in combos]))
        expected = {(-1, -1): -1, (-1, 1): 1j, (1, -1): -1j, (1, 1): 1}
        for (i, q), val in zip(combos, y):
            with self.subTest(I=i, Q=q):
                self.assertEqual(complex(val), expected[(i, q)])
        x = np.array([expected[c] for c in combos])
        dq = dqpsk_encode(x)
        np.testing.assert_allclose(np.abs(dq), math.sqrt(2), rtol=1e-15)
        np.testing.assert_array_equal(dq[:4], x[:4] * (1 + 1j))

    def test_quantization_floor_formula_matches_fixed_point_doc(self):
        values = np.array([0.5, -0.5, 0.999, -1.0])
        got = quantize_complex_floor(values, 6)
        np.testing.assert_array_equal(got.real, np.floor(values * 31))
        self.assertEqual(int(got.real[0]), 15)
        self.assertEqual(int(got.real[1]), -16)
        self.assertEqual(int(got.real[3]), -31)

    def test_symbol_address_first_bit_is_msb_at_250k(self):
        bits = np.array([1,0,1,1,0,0], dtype=np.int8)
        self.assertEqual(int(serial_to_symbols(bits, RATE_250K)[0]), 44)

    def test_phr_field_boundaries(self):
        self.assertEqual(phr_bits(0).tolist(), [0]*7 + [0]*5)
        self.assertEqual(phr_bits(127).tolist(), [1]*7 + [0]*5)
        self.assertEqual(phr_bits(42).tolist(), [0,1,0,1,0,1,0] + [0]*5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
