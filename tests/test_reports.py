#!/usr/bin/env python3
import sys
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from parse_vivado_reports import parse_timing_summary, parse_utilization, parse_clock_file, parse_reports


class ReportParserTests(unittest.TestCase):
    def test_positive_timing_summary(self):
        text = """
Design Timing Summary
WNS(ns)      TNS(ns)  TNS Failing Endpoints
-------      -------  ---------------------
  0.214        0.000                      0
"""
        got = parse_timing_summary(text)
        self.assertEqual(got["wns_ns"], 0.214)
        self.assertEqual(got["tns_ns"], 0.0)
        self.assertEqual(got["timing_status"], "PASS")

    def test_negative_slack_is_fail(self):
        text = """
WNS(ns) TNS(ns) TNS Failing Endpoints
------- ------- ---------------------
-0.125  -4.250  18
"""
        got = parse_timing_summary(text)
        self.assertEqual(got["timing_status"], "FAIL")

    def test_missing_clock_is_not_measured(self):
        got = parse_timing_summary("There are no clocks found in the design.\n")
        self.assertEqual(got["timing_status"], "NOT_MEASURED")
        self.assertFalse(got["has_clock_evidence"])

    def test_positive_unconstrained_path_count_invalidates_timing(self):
        text = """
WNS(ns) TNS(ns) TNS Failing Endpoints
------- ------- ---------------------
0.250 0.000 0
Unconstrained Paths: 3
"""
        got = parse_timing_summary(text)
        self.assertEqual(got["unconstrained_paths"], 3)
        self.assertEqual(got["timing_status"], "INVALID_UNCONSTRAINED")

    def test_utilization_aliases(self):
        text = """
| Site Type         | Used | Fixed | Available | Util% |
| CLB LUTs          | 123  | 0     | 53200     | 0.23  |
| CLB Registers     | 456  | 0     | 106400    | 0.43  |
| Block RAM Tile    | 2    | 0     | 140       | 1.43  |
| DSPs              | 4    | 0     | 220       | 1.82  |
| Bonded IOB        | 30   | 0     | 200       | 15.00 |
| BUFGCTRL           | 1    | 0     | 32        | 3.13  |
"""
        got = parse_utilization(text)
        self.assertEqual(got["lut"]["used"], 123)
        self.assertEqual(got["ff"]["used"], 456)
        self.assertEqual(got["bram"]["used"], 2)
        self.assertEqual(got["dsp"]["used"], 4)
        self.assertEqual(got["io"]["used"], 30)
        self.assertEqual(got["bufg"]["used"], 1)

    def test_clock_evidence(self):
        got = parse_clock_file("sys_clk period_ns=31.250\n")
        self.assertEqual(got["clocks"], [{"name": "sys_clk", "period_ns": 31.25}])

    def test_directory_parser_does_not_invent_missing_metrics(self):
        with tempfile.TemporaryDirectory() as td:
            data = parse_reports(Path(td))
            self.assertNotIn("timing", data)
            self.assertNotIn("utilization", data)
            self.assertNotIn("clocks", data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
