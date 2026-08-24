#!/usr/bin/env python3
"""ModelSim-based lint stage.

Mirrors scripts/run_lint.sh for environments without Verilator: compiles the
synthesizable RTL with `vlog -sv -lint` and treats every diagnostic as fatal.
The Verilator `-Wall` gate remains the stricter reference flow in CI; this
stage guarantees a lint pass also exists where only ModelSim is installed.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIM_DIR = ROOT / "results" / "msim"

RTL_FILES = [
    "rtl/css_phy_pkg.sv", "rtl/payload_ram.sv", "rtl/phr_generator.sv",
    "rtl/zero_pad_framer.sv", "rtl/iq_demux.sv", "rtl/symbol_mapper_1m.sv",
    "rtl/symbol_mapper_250k.sv", "rtl/bit_interleaver.sv", "rtl/preamble_sfd_rom.sv",
    "rtl/qpsk_mapper.sv", "rtl/dqpsk_encoder.sv", "rtl/chirp_rom.sv",
    "rtl/csk_modulator.sv", "rtl/css_tx_controller.sv", "rtl/css_phy_tx_top.sv",
]
DIAG_RE = re.compile(r"^\*\* (Error|Warning|Failure|Fatal)", re.MULTILINE)


def main() -> int:
    def find(name: str) -> str | None:
        bindir = os.environ.get("MODELSIM_BIN", "").strip()
        if bindir:
            candidate = Path(bindir) / name
            if candidate.exists():
                return str(candidate)
        return shutil.which(name)

    vlib_tool, vlog = find("vlib"), find("vlog")
    if not vlib_tool or not vlog:
        print("BLOCKED: ModelSim/Questasim (vlib + vlog) is not installed.", file=sys.stderr)
        return 2

    libpath = SIM_DIR / "work_lint"
    if libpath.exists():
        shutil.rmtree(libpath)
    subprocess.run([vlib_tool, str(libpath)], cwd=ROOT, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    cmd = [vlog, "-sv", "-lint", "-work", str(libpath)] + RTL_FILES
    proc = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, errors="replace")
    out = proc.stdout.replace("\r\n", "\n")
    log_path = SIM_DIR / "logs" / "lint_msim.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(out, encoding="utf-8")

    problems = []
    if proc.returncode != 0:
        problems.append(f"exit code {proc.returncode}")
    diagnostics = DIAG_RE.findall(out)
    if diagnostics:
        problems.append(f"{len(diagnostics)} diagnostic(s)")
        print(out)
    if problems:
        print(f"FAIL lint (ModelSim): {'; '.join(problems)}")
        return 1
    print("PASS lint (ModelSim): vlog -sv -lint clean on 15 RTL files "
          "(warnings treated as fatal)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
