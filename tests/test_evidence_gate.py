#!/usr/bin/env python3
"""Self-tests for the CI evidence gate (scripts/require_ci_evidence.py).

The gate blocks CI on missing or corrupted verification evidence; these tests
prove both directions: a complete evidence bundle passes, and removing or
corrupting any required item is detected. This is the negative-control
discipline applied to the gate itself.
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

_spec = importlib.util.spec_from_file_location(
    "require_ci_evidence", ROOT / "scripts" / "require_ci_evidence.py")
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

# Suite size guarded by the gate; keep in sync with tests/ discovery count.
MIN_PYTHON_TESTS = 63


def build_rtl_log() -> str:
    lines = []
    for marker in gate.REQUIRED_UNIT_MARKERS:
        lines.append(marker)
    for rate in (0, 1):
        lines.append(f"PASS tb_css_phy_protocol rate={rate} samples=100")
        for plen in gate.REQUIRED_PAYLOADS:
            lines.append(f"PASS tb_css_tx_controller rate={rate} plen={plen} chips=10")
            lines.append(f"PASS tb_css_phy_tx_top rate={rate} plen={plen} chirp=1 sdiv=1 samples=20")
        lines.append(f"PASS tb_css_phy_tx_multi rate={rate} packets=3 lens=25,25,127")
        lines.append(f"PASS tb_css_phy_tx_reset_sweep rate={rate} resets=6 plen=25")
        lines.append(f"PASS tb_css_phy_tx_stress rate={rate} packets=24")
        for m in (2, 3, 4):
            lines.append(f"PASS tb_css_phy_tx_top rate={rate} plen=25 chirp={m} sdiv=1 samples=30")
        for div in (2, 5):
            lines.append(f"PASS tb_css_phy_tx_top rate={rate} plen=25 chirp=1 sdiv={div} samples=40")
    lines.append("PASS: complete RTL regression")
    return "\n".join(lines) + "\n"


def build_summary() -> dict:
    stages = {name: {"name": name, "status": "PASS"} for name in gate.REQUIRED_STAGES}
    mse_stage = stages["Fixed-point MSE calculation"]
    mse_stage["measured_floor_mse_bits6"] = 0.000891330083552
    mse_stage["threshold"] = 0.005
    return {"python_test_count": MIN_PYTHON_TESTS, "stages": list(stages.values())}


class EvidenceGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.rtl = Path(self.tmp.name) / "rtl_regression.log"
        self.lint = Path(self.tmp.name) / "verilator_lint.log"
        self.rtl.write_text(build_rtl_log(), encoding="utf-8")
        self.lint.write_text("Verilator lint completed without diagnostics\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def check_logs(self) -> list[str]:
        return gate.validate_logs(rtl_log=self.rtl, lint_log=self.lint)

    def test_valid_bundle_passes(self):
        self.assertEqual(self.check_logs(), [])
        self.assertEqual(gate.validate_summary(build_summary()), [])

    def test_missing_rtl_log_detected(self):
        self.rtl.unlink()
        errors = self.check_logs()
        self.assertTrue(any("missing RTL regression log" in e for e in errors))

    def test_missing_completion_marker_detected(self):
        self.rtl.write_text(build_rtl_log().replace("PASS: complete RTL regression", ""),
                            encoding="utf-8")
        errors = self.check_logs()
        self.assertTrue(any("completion marker" in e for e in errors))

    def test_removed_unit_marker_detected(self):
        text = build_rtl_log().replace("PASS tb_csk_modulator\n", "")
        self.rtl.write_text(text, encoding="utf-8")
        errors = self.check_logs()
        self.assertTrue(any("tb_csk_modulator" in e for e in errors))

    def test_tampered_matrix_row_detected(self):
        # Relabeling a matrix PASS line (wrong payload length) must break the
        # required per-length evidence marker and fail the gate.
        text = build_rtl_log().replace(
            "PASS tb_css_phy_tx_top rate=0 plen=127 chirp=1 sdiv=1 samples=20",
            "PASS tb_css_phy_tx_top rate=0 plen=126 chirp=1 sdiv=1 samples=20")
        self.assertNotEqual(text, build_rtl_log())
        self.rtl.write_text(text, encoding="utf-8")
        errors = self.check_logs()
        self.assertTrue(any("top-level matrix evidence missing" in e and "plen=127" in e
                            for e in errors))

    def test_removed_multi_packet_marker_detected(self):
        text = build_rtl_log().replace(
            "PASS tb_css_phy_tx_multi rate=1 packets=3 lens=25,25,127\n", "")
        self.assertNotEqual(text, build_rtl_log())
        self.rtl.write_text(text, encoding="utf-8")
        errors = self.check_logs()
        self.assertTrue(any("back-to-back packet evidence missing" in e and "rate=1" in e
                            for e in errors))

    def test_removed_reset_sweep_marker_detected(self):
        text = build_rtl_log().replace(
            "PASS tb_css_phy_tx_reset_sweep rate=0 resets=6 plen=25\n", "")
        self.rtl.write_text(text, encoding="utf-8")
        errors = self.check_logs()
        self.assertTrue(any("reset sweep evidence missing" in e and "rate=0" in e
                            for e in errors))

    def test_removed_stress_marker_detected(self):
        text = build_rtl_log().replace(
            "PASS tb_css_phy_tx_stress rate=1 packets=24\n", "")
        self.rtl.write_text(text, encoding="utf-8")
        errors = self.check_logs()
        self.assertTrue(any(
            "stress evidence missing" in e and "rate=1" in e
            for e in errors
        ))

    def test_removed_chirp_sweep_marker_detected(self):
        text = build_rtl_log().replace(
            "PASS tb_css_phy_tx_top rate=1 plen=25 chirp=3 sdiv=1 samples=30\n", "")
        self.rtl.write_text(text, encoding="utf-8")
        errors = self.check_logs()
        self.assertTrue(any("chirp sweep evidence missing" in e and "chirp=3" in e
                            for e in errors))

    def test_removed_sample_divider_marker_detected(self):
        text = build_rtl_log().replace(
            "PASS tb_css_phy_tx_top rate=0 plen=25 chirp=1 sdiv=5 samples=40\n", "")
        self.rtl.write_text(text, encoding="utf-8")
        errors = self.check_logs()
        self.assertTrue(any("SAMPLE_DIV sweep evidence missing" in e and "sdiv=5" in e
                            for e in errors))

    def test_fatal_in_regression_transcript_detected(self):
        # A transcript that contains error/fatal diagnostics must fail the gate
        # even if a completion marker is present (protects against drivers that
        # continue after a failed simulation).
        text = build_rtl_log() + "** Fatal: scoreboard mismatch\n"
        self.rtl.write_text(text, encoding="utf-8")
        errors = self.check_logs()
        self.assertTrue(any("error/fatal diagnostics" in e for e in errors))

    def test_lint_warning_detected(self):
        self.lint.write_text("%Warning-WIDTHEXPAND: blah\n", encoding="utf-8")
        errors = self.check_logs()
        self.assertTrue(any("lint log contains warning/error" in e for e in errors))

    def test_summary_stage_blocked_rejected(self):
        summary = build_summary()
        summary["stages"][0]["status"] = "BLOCKED"
        errors = gate.validate_summary(summary)
        self.assertTrue(any("did not PASS" in e and "Golden vector" in e for e in errors))

    def test_summary_stage_missing_rejected(self):
        summary = build_summary()
        summary["stages"] = summary["stages"][1:]
        errors = gate.validate_summary(summary)
        self.assertTrue(any("required stage missing" in e for e in errors))

    def test_python_count_below_minimum_rejected(self):
        summary = build_summary()
        summary["python_test_count"] = MIN_PYTHON_TESTS - 1
        errors = gate.validate_summary(summary)
        self.assertTrue(any("below required" in e for e in errors))

    def test_mse_above_threshold_rejected(self):
        summary = build_summary()
        for stage in summary["stages"]:
            if stage["name"] == "Fixed-point MSE calculation":
                stage["measured_floor_mse_bits6"] = 0.006
        errors = gate.validate_summary(summary)
        self.assertTrue(any("MSE acceptance failed" in e for e in errors))

    def test_mse_malformed_rejected(self):
        summary = build_summary()
        for stage in summary["stages"]:
            if stage["name"] == "Fixed-point MSE calculation":
                del stage["measured_floor_mse_bits6"]
        errors = gate.validate_summary(summary)
        self.assertTrue(any("MSE evidence is missing or malformed" in e for e in errors))


if __name__ == "__main__":
    unittest.main(verbosity=2)
