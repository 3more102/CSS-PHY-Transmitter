#!/usr/bin/env python3
"""Fail CI unless required open-source verification evidence actually passed.

`run_verification.py` deliberately reports unavailable optional tools as BLOCKED
so local development remains truthful. GitHub Actions explicitly installs
Icarus Verilog and Verilator, therefore those stages are mandatory in CI and
must also leave complete, internally consistent evidence logs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
SUMMARY = REPORTS / "verification_summary.json"
RTL_LOG = REPORTS / "rtl_regression.log"
LINT_LOG = REPORTS / "verilator_lint.log"

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
REQUIRED_PAYLOADS = (0, 1, 3, 25, 127)
REQUIRED_UNIT_MARKERS = (
    "PASS tb_payload_ram",
    "PASS tb_phr_generator",
    "PASS tb_zero_pad_framer",
    "PASS tb_iq_demux",
    "PASS tb_preamble_sfd_rom",
    "PASS tb_symbol_mapper_1m",
    "PASS tb_symbol_mapper_250k",
    "PASS tb_interleaver",
    "PASS tb_qpsk_mapper",
    "PASS tb_dqpsk_encoder",
    "PASS tb_chirp_rom",
    "PASS tb_csk_modulator",
)


def validate_summary(payload: dict[str, Any]) -> list[str]:
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


def validate_logs() -> list[str]:
    errors: list[str] = []

    if not LINT_LOG.is_file():
        errors.append("missing Verilator lint log")
    else:
        lint_text = LINT_LOG.read_text(encoding="utf-8", errors="replace")
        if "%Warning-" in lint_text or "%Error-" in lint_text:
            errors.append("Verilator lint log contains warning/error diagnostics")

    if not RTL_LOG.is_file():
        errors.append("missing RTL regression log")
        return errors

    rtl_text = RTL_LOG.read_text(encoding="utf-8", errors="replace")
    if "PASS: complete RTL regression" not in rtl_text:
        errors.append("RTL regression completion marker is missing")

    for marker in REQUIRED_UNIT_MARKERS:
        if marker not in rtl_text:
            errors.append(f"RTL unit evidence missing: {marker}")

    for rate in (0, 1):
        protocol_marker = f"PASS tb_css_phy_protocol rate={rate}"
        if protocol_marker not in rtl_text:
            errors.append(f"RTL protocol evidence missing: {protocol_marker}")
        for plen in REQUIRED_PAYLOADS:
            controller_marker = f"PASS tb_css_tx_controller rate={rate} plen={plen}"
            top_marker = f"PASS tb_css_phy_tx_top rate={rate} plen={plen}"
            if controller_marker not in rtl_text:
                errors.append(f"RTL controller matrix evidence missing: {controller_marker}")
            if top_marker not in rtl_text:
                errors.append(f"RTL top-level matrix evidence missing: {top_marker}")
        multi_marker = f"PASS tb_css_phy_tx_multi rate={rate} packets=3 lens=25,25,127"
        if multi_marker not in rtl_text:
            errors.append(f"RTL back-to-back packet evidence missing: {multi_marker}")
        sweep_marker = f"PASS tb_css_phy_tx_reset_sweep rate={rate} resets=6 plen=25"
        if sweep_marker not in rtl_text:
            errors.append(f"RTL mid-stream reset sweep evidence missing: {sweep_marker}")

    for rate in (0, 1):
        for m in (2, 3, 4):
            chirp_marker = f"PASS tb_css_phy_tx_top rate={rate} plen=25 chirp={m} sdiv=1 samples="
            if chirp_marker not in rtl_text:
                errors.append(f"RTL chirp sweep evidence missing: {chirp_marker}")
        for div in (2, 5):
            sdiv_marker = f"PASS tb_css_phy_tx_top rate={rate} plen=25 chirp=1 sdiv={div} samples="
            if sdiv_marker not in rtl_text:
                errors.append(f"RTL SAMPLE_DIV sweep evidence missing: {sdiv_marker}")

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

    errors = validate_summary(payload) + validate_logs()
    if errors:
        print("CI evidence gate: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "CI evidence gate: PASS "
        f"({payload.get('python_test_count')} Python tests; all RTL unit/matrix markers present; "
        "strict Verilator lint clean)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
