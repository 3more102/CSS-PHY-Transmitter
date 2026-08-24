#!/usr/bin/env python3
"""Evidence-producing top-level verification driver for the CSS PHY project.

Statuses are deliberately strict:
  PASS    command was executed and succeeded;
  FAIL    command was executed and failed;
  SKIP    stage is intentionally not applicable;
  BLOCKED required external tool/target is unavailable.

BLOCKED is never converted into PASS.  The script writes both machine-readable
JSON and a concise text summary under reports/.
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)
SUMMARY_JSON = REPORTS / "verification_summary.json"
SUMMARY_TXT = REPORTS / "verification_summary.txt"

TOOLS = ["python3", "iverilog", "vvp", "verilator", "vlog", "vsim", "octave", "matlab", "vivado", "quartus_sh"]


def tool_map() -> dict[str, str | None]:
    return {name: shutil.which(name) for name in TOOLS}


def run_command(name: str, cmd: list[str], log_name: str, env: dict[str, str] | None = None) -> dict[str, Any]:
    log_path = REPORTS / log_name
    proc = subprocess.run(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
    log_path.write_text(proc.stdout, encoding="utf-8")
    return {"name": name, "status": "PASS" if proc.returncode == 0 else "FAIL", "command": cmd, "returncode": proc.returncode, "log": str(log_path.relative_to(ROOT))}


def blocked(name: str, reason: str) -> dict[str, Any]:
    return {"name": name, "status": "BLOCKED", "reason": reason}


def git_state() -> dict[str, Any]:
    def git(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    try:
        return {"branch": git("branch", "--show-current"), "head": git("rev-parse", "HEAD"), "tags_at_head": [x for x in git("tag", "--points-at", "HEAD").splitlines() if x], "working_tree_short": git("status", "--short").splitlines()}
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        return {"error": str(exc)}


def run_python_test_file(filename: str, label: str) -> dict[str, Any]:
    result = run_command(label, [sys.executable, f"tests/{filename}"], f"{Path(filename).stem}.log")
    text = (REPORTS / f"{Path(filename).stem}.log").read_text(encoding="utf-8")
    match = re.search(r"Ran\s+(\d+)\s+tests?", text)
    if match:
        result["test_count"] = int(match.group(1))
    return result


def read_mse() -> tuple[float, float]:
    path = REPORTS / "mse_results.csv"
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    row6 = next(row for row in rows if int(row["bits"]) == 6)
    return float(row6["floor_mse"]), 0.005


def main() -> int:
    tools = tool_map()
    stages: list[dict[str, Any]] = []
    stages.append(run_command("Golden vector / ROM regeneration", [sys.executable, "matlab/vector_generation/generate_vectors.py"], "vector_generation.log"))
    mse_stage = run_command("Fixed-point MSE calculation", [sys.executable, "matlab/mse/mse_analysis.py"], "mse_analysis.log")
    if mse_stage["status"] == "PASS":
        try:
            mse, threshold = read_mse()
            mse_stage["measured_floor_mse_bits6"] = mse
            mse_stage["threshold"] = threshold
            if not mse < threshold:
                mse_stage["status"] = "FAIL"
                mse_stage["reason"] = f"Measured MSE {mse} is not below {threshold}"
        except Exception as exc:
            mse_stage["status"] = "FAIL"
            mse_stage["reason"] = f"Could not parse MSE evidence: {exc}"
    stages.append(mse_stage)

    test_groups = [
        ("test_reference.py", "Reference equivalence tests"),
        ("test_architecture.py", "Architecture equivalence tests"),
        ("test_artifacts.py", "Artifact / synthesis-static tests"),
        ("test_bit_order.py", "Directed bit-order tests"),
        ("test_randomized.py", "Deterministic randomized tests"),
        ("test_reports.py", "EDA report parser tests"),
    ]
    for filename, label in test_groups:
        stages.append(run_python_test_file(filename, label))

    if tools["matlab"]:
        stages.append(run_command("Native MATLAB reference execution", [tools["matlab"], "-batch", "cd('matlab/original'); addpath('common'); addpath('transmitter'); run('runMe.m');"], "matlab_run.log"))
    else:
        stages.append(blocked("Native MATLAB reference execution", "MATLAB is not installed"))

    if tools["iverilog"] and tools["vvp"]:
        stages.append(run_command("RTL simulation regression", ["bash", "scripts/run_rtl_tests.sh"], "rtl_regression.log"))
    elif shutil.which("vlog") or shutil.which("vsim") or os.environ.get("MODELSIM_BIN"):
        # Fallback: same regression matrix executed by ModelSim/Questasim when
        # Icarus Verilog is unavailable. Same PASS markers, same strictness.
        stages.append(run_command("RTL simulation regression (ModelSim)", [sys.executable, "scripts/run_rtl_tests_msim.py"], "rtl_regression_msim.log"))
    else:
        stages.append(blocked("RTL simulation regression", "Missing tool(s): iverilog, vvp (no vlog/vsim fallback)"))

    if tools["verilator"]:
        stages.append(run_command("Verilator lint", ["bash", "scripts/run_lint.sh"], "verilator_lint.log"))
    else:
        stages.append(blocked("Verilator lint", "Verilator is not installed"))

    fpga_part = os.environ.get("FPGA_PART", "").strip()
    if not tools["vivado"]:
        stages.append(blocked("Vivado synthesis", "Vivado is not installed"))
        stages.append(blocked("Vivado implementation / timing", "Vivado is not installed"))
    elif not fpga_part:
        stages.append(blocked("Vivado synthesis", "FPGA_PART is not defined; refusing to invent a target"))
        stages.append(blocked("Vivado implementation / timing", "FPGA_PART is not defined; refusing to invent a target"))
    else:
        env = os.environ.copy()
        synth = run_command("Vivado synthesis", [tools["vivado"], "-mode", "batch", "-source", "scripts/vivado_synth.tcl", "-nojournal", "-nolog"], "vivado_synthesis.log", env=env)
        stages.append(synth)
        if synth["status"] == "PASS":
            impl = run_command("Vivado implementation / timing", [tools["vivado"], "-mode", "batch", "-source", "scripts/vivado_impl.tcl", "-nojournal", "-nolog"], "vivado_implementation.log", env=env)
            stages.append(impl)
            if impl["status"] == "PASS":
                stages.append(run_command("Vivado report extraction", [sys.executable, "scripts/parse_vivado_reports.py"], "vivado_report_parse.log"))
        else:
            stages.append(blocked("Vivado implementation / timing", "Synthesis did not pass"))

    status_counts = {key: sum(1 for s in stages if s["status"] == key) for key in ("PASS", "FAIL", "SKIP", "BLOCKED")}
    total_python_tests = sum(int(s.get("test_count", 0)) for s in stages)
    payload = {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "git": git_state(), "tools": tools, "fixed_seed": "0x802154", "python_test_count": total_python_tests, "status_counts": status_counts, "stages": stages}
    SUMMARY_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = ["CSS PHY Transmitter Verification Summary", "======================================", f"Generated UTC: {payload['generated_at_utc']}", f"Branch: {payload['git'].get('branch', 'unknown')}", f"HEAD: {payload['git'].get('head', 'unknown')}", f"Python tests executed: {total_python_tests}", f"Counts: PASS={status_counts['PASS']} FAIL={status_counts['FAIL']} SKIP={status_counts['SKIP']} BLOCKED={status_counts['BLOCKED']}", ""]
    for stage in stages:
        extra = ""
        if "measured_floor_mse_bits6" in stage:
            extra = f" (MSE={stage['measured_floor_mse_bits6']:.12g}, threshold < {stage['threshold']})"
        elif stage.get("reason"):
            extra = f" — {stage['reason']}"
        elif stage.get("test_count") is not None:
            extra = f" ({stage['test_count']} tests)"
        lines.append(f"[{stage['status']}] {stage['name']}{extra}")
    lines.extend(["", "Tool availability:", *[f"- {name}: {path if path else 'MISSING'}" for name, path in tools.items()], "", "PASS means executed successfully. BLOCKED means required tool/target unavailable."])
    SUMMARY_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(SUMMARY_TXT.read_text(encoding="utf-8"), end="")
    return 1 if status_counts["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
