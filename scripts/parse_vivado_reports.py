#!/usr/bin/env python3
"""Parse selected Vivado implementation evidence into machine-readable JSON.

This parser never invents missing metrics.  A field is emitted only when the
corresponding report contains a recognized value.  Timing is marked PASS only
when a clock is present and both WNS/TNS are non-negative.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

FLOAT_RE = r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?"


def parse_timing_summary(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    lower = text.lower()
    out["has_clock_evidence"] = not any(
        phrase in lower for phrase in (
            "no clocks found", "there are no clocks", "no clock", "no constrained paths"
        )
    )

    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if "WNS(ns)" in line and "TNS(ns)" in line:
            for candidate in lines[idx + 1 : idx + 8]:
                if re.fullmatch(r"[\s\-]+", candidate):
                    continue
                nums = re.findall(FLOAT_RE, candidate)
                if len(nums) >= 2:
                    out["wns_ns"] = float(nums[0])
                    out["tns_ns"] = float(nums[1])
                    break
            if "wns_ns" in out:
                break

    unconstrained = re.search(r"Unconstrained\s+Paths?\s*[:|]\s*(\d+)", text, re.IGNORECASE)
    if unconstrained:
        out["unconstrained_paths"] = int(unconstrained.group(1))

    if out.get("has_clock_evidence") and "wns_ns" in out and "tns_ns" in out:
        if out.get("unconstrained_paths", 0) > 0:
            out["timing_status"] = "INVALID_UNCONSTRAINED"
        else:
            out["timing_status"] = "PASS" if out["wns_ns"] >= 0.0 and out["tns_ns"] >= 0.0 else "FAIL"
    else:
        out["timing_status"] = "NOT_MEASURED"
    return out


def _table_metric(text: str, names: tuple[str, ...]) -> dict[str, float | int] | None:
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells:
            continue
        label = cells[0].lower()
        if not any(name.lower() == label for name in names):
            continue
        numeric = []
        for cell in cells[1:]:
            clean = cell.replace(",", "").replace("%", "").strip()
            if re.fullmatch(FLOAT_RE, clean):
                numeric.append(float(clean))
        if not numeric:
            return None
        result: dict[str, float | int] = {"used": int(numeric[0]) if numeric[0].is_integer() else numeric[0]}
        if len(numeric) >= 3:
            result["available"] = int(numeric[-2]) if numeric[-2].is_integer() else numeric[-2]
            result["util_percent"] = numeric[-1]
        return result
    return None


def parse_utilization(text: str) -> dict[str, Any]:
    aliases = {
        "lut": ("CLB LUTs", "Slice LUTs"),
        "ff": ("CLB Registers", "Slice Registers"),
        "bram": ("Block RAM Tile",),
        "dsp": ("DSPs", "DSP48 Blocks"),
        "io": ("Bonded IOB",),
        "bufg": ("BUFGCTRL", "BUFG"),
    }
    out: dict[str, Any] = {}
    for key, names in aliases.items():
        value = _table_metric(text, names)
        if value is not None:
            out[key] = value
    return out


def parse_clock_file(text: str) -> dict[str, Any]:
    clocks = []
    for line in text.splitlines():
        match = re.match(r"(\S+)\s+period_ns=(%s)" % FLOAT_RE, line.strip())
        if match:
            clocks.append({"name": match.group(1), "period_ns": float(match.group(2))})
    return {"clocks": clocks}


def parse_reports(report_dir: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"report_dir": str(report_dir)}
    timing = report_dir / "impl_timing_summary.rpt"
    util = report_dir / "impl_utilization.rpt"
    clocks = report_dir / "impl_clocks.txt"
    if timing.exists():
        result["timing"] = parse_timing_summary(timing.read_text(errors="replace"))
    if util.exists():
        result["utilization"] = parse_utilization(util.read_text(errors="replace"))
    if clocks.exists():
        result.update(parse_clock_file(clocks.read_text(errors="replace")))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-dir", type=Path, default=Path("reports/implementation"))
    parser.add_argument("--output", type=Path, default=Path("reports/implementation/impl_metrics.json"))
    args = parser.parse_args()
    data = parse_reports(args.report_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    timing_status = data.get("timing", {}).get("timing_status")
    return 1 if timing_status in {"FAIL", "INVALID_UNCONSTRAINED"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
