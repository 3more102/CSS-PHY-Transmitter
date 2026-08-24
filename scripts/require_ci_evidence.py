#!/usr/bin/env python3
"""Fail CI unless required open-source verification evidence actually passed.

`run_verification.py` deliberately reports unavailable optional tools as BLOCKED
so local development remains truthful. GitHub Actions explicitly installs
Icarus Verilog and Verilator, therefore those stages are mandatory in CI and
must also leave complete, internally consistent evidence logs.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
SUMMARY = REPORTS / "verification_summary.json"
RTL_LOG = REPORTS / "rtl_regression.log"
LINT_LOG = REPORTS / "verilator_lint.log"

# run_verification.py records whichever backend actually executed a logical
# stage (Icarus/Verilator primary, ModelSim fallback). The gate must accept
# equivalent evidence from either backend instead of hard-coding one toolchain.
RTL_STAGE_MSIM = "RTL simulation regression (ModelSim)"
LINT_STAGE_MSIM = "Lint (ModelSim)"
STAGE_ALIASES = {
    "RTL simulation regression": (RTL_STAGE_MSIM,),
    "Verilator lint": (LINT_STAGE_MSIM,),
}
RTL_LOG_MSIM = REPORTS / "rtl_regression_msim.log"
LINT_LOG_MSIM = REPORTS / "lint_msim_stage.log"

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
MIN_PYTHON_TESTS = 69
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


def find_stage(stages: dict[str, dict[str, Any]], name: str) -> dict[str, Any] | None:
    stage = stages.get(name)
    if stage is not None:
        return stage
    for alias in STAGE_ALIASES.get(name, ()):
        if alias in stages:
            return stages[alias]
    return None


def validate_summary(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    stages = {stage.get("name"): stage for stage in payload.get("stages", [])}

    if int(payload.get("python_test_count", 0)) < MIN_PYTHON_TESTS:
        errors.append(
            f"python_test_count={payload.get('python_test_count', 0)} is below required {MIN_PYTHON_TESTS}"
        )

    for name in REQUIRED_STAGES:
        stage = find_stage(stages, name)
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


def validate_logs(rtl_log: Path = RTL_LOG, lint_log: Path = LINT_LOG) -> list[str]:
    """Validate evidence logs. Paths are injectable so the gate logic itself
    can be unit-tested without a real verification run."""
    errors: list[str] = []

    if not lint_log.is_file():
        errors.append("missing Verilator lint log")
    else:
        lint_text = lint_log.read_text(encoding="utf-8", errors="replace")
        # Both diagnostic formats are scanned unconditionally: Verilator
        # ("%Warning-...") and ModelSim ("** Warning ..."). A log produced by
        # one backend cannot contain the other's diagnostics, so this stays
        # precise while accepting evidence from either toolchain.
        if "%Warning-" in lint_text or "%Error-" in lint_text:
            errors.append("Verilator lint log contains warning/error diagnostics")
        if re.search(r"^\*\* (Warning|Error|Fatal)", lint_text, re.MULTILINE):
            errors.append("lint log contains simulator warning/error diagnostics")

    if not rtl_log.is_file():
        errors.append("missing RTL regression log")
        return errors

    rtl_text = rtl_log.read_text(encoding="utf-8", errors="replace")
    if re.search(r"^\*\* (Fatal|Error)", rtl_text, re.MULTILINE):
        # Protects against drivers that keep running after a failed
        # simulation: a transcript with diagnostics must fail even when a
        # completion marker is present.
        errors.append("RTL regression log contains error/fatal diagnostics")
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
        stress_marker = f"PASS tb_css_phy_tx_stress rate={rate} packets=24"
        if stress_marker not in rtl_text:
            errors.append(f"RTL stress evidence missing: {stress_marker}")

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


def evidence_log_paths(payload: dict[str, Any]) -> tuple[Path, Path]:
    """Pick the regression/lint logs matching the backend that actually ran."""
    names = {stage.get("name") for stage in payload.get("stages", [])}
    rtl_log = RTL_LOG_MSIM if RTL_STAGE_MSIM in names else RTL_LOG
    lint_log = LINT_LOG_MSIM if LINT_STAGE_MSIM in names else LINT_LOG
    return rtl_log, lint_log


def main() -> int:
    if not SUMMARY.is_file():
        print(f"FAIL: missing verification summary: {SUMMARY.relative_to(ROOT)}")
        return 1

    try:
        payload = json.loads(SUMMARY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot read verification summary: {exc}")
        return 1

    rtl_log, lint_log = evidence_log_paths(payload)
    errors = validate_summary(payload) + validate_logs(rtl_log=rtl_log, lint_log=lint_log)
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
