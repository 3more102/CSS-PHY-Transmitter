#!/usr/bin/env python3
"""Fail CI unless required open-source verification stages actually passed.

`run_verification.py` deliberately reports unavailable optional tools as BLOCKED
so local development remains truthful.  GitHub Actions, however, explicitly
installs Icarus Verilog and Verilator; therefore those stages are mandatory in
CI and a BLOCKED result must not produce a green workflow.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "reports" / "verification_summary.json"
REQUIRED_STAGES = (
    "Golden vector / ROM regeneration",
    "Fixed-point MSE calculation",
    "Reference equivalence tests",
    "Architecture equivalence tests",
    "Artifact / synthesis-static tests",
    "Directed bit-order tests",
    "Deterministic randomized tests",
    "EDA report parser tests",
    "RTL simulation regression",
    "Verilator lint",
)
MIN_PYTHON_TESTS = 46


def validate(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    stages = {stage.get("name"): stage for stage in payload.get("stages", [])}

    if int(payload.get("python_test_count", 0)) < MIN_PYTHON_TESTS:
        errors.append(
            f"python_test_count={payload.get('python_test_count', 0)} is below required {MIN_PYTHON_TESTS}"
        )

    for name in REQUIRED_STAGES:
        stage = stages.get(name)
        if stage is None:
            errors.append(f"required stage missing: {name}")
            continue
        if stage.get("status") != "PASS":
            detail = stage.get("reason") or f"status={stage.get('status')}"
            errors.append(f"required stage did not PASS: {name}: {detail}")

    mse_stage = stages.get("Fixed-point MSE calculation", {})
    try:
        mse = float(mse_stage["measured_floor_mse_bits6"])
        threshold = float(mse_stage["threshold"])
        if not mse < threshold:
            errors.append(f"MSE acceptance failed: {mse} is not below {threshold}")
    except (KeyError, TypeError, ValueError):
        errors.append("MSE evidence is missing or malformed")

    return errors


def main() -> int:
    if not SUMMARY.is_file():
        print(f"FAIL: missing verification summary: {SUMMARY.relative_to(ROOT)}")
        return 1

    try:
        payload = json.loads(SUMMARY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot read verification summary: {exc}")
        return 1

    errors = validate(payload)
    if errors:
        print("CI evidence gate: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "CI evidence gate: PASS "
        f"({payload.get('python_test_count')} Python tests; RTL simulation PASS; Verilator lint PASS)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
