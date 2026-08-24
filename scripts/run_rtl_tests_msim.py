#!/usr/bin/env python3
"""ModelSim-based RTL regression driver.

Mirrors scripts/run_rtl_tests.sh (same test list, same golden vectors, same
PASS markers) for environments where Icarus Verilog is unavailable but
ModelSim/Questasim (vlog/vsim) is installed.

Strictness contract:
  * every vsim/vlog invocation must exit 0;
  * every test transcript must contain its expected PASS marker;
  * no transcript may contain "** Error", "** Failure" or "** Fatal"
    diagnostics (this ModelSim vintage exits 0 even after $fatal, so the
    transcript scan is mandatory, not optional).
Any violation fails the whole driver non-zero.
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
UNIT_TBS = [
    "tb_payload_ram", "tb_phr_generator", "tb_zero_pad_framer", "tb_iq_demux",
    "tb_preamble_sfd_rom", "tb_symbol_mapper_1m", "tb_symbol_mapper_250k",
    "tb_interleaver", "tb_qpsk_mapper", "tb_dqpsk_encoder", "tb_chirp_rom",
    "tb_csk_modulator",
]
RATE_TBS = ["tb_css_tx_controller", "tb_css_phy_tx_top", "tb_css_phy_protocol",
            "tb_css_phy_tx_multi"]
LENGTHS = [0, 1, 3, 25, 127]

ERROR_RE = re.compile(r"^\*\* (Error|Failure|Fatal)", re.MULTILINE)


def find_tool(name: str) -> str | None:
    bindir = os.environ.get("MODELSIM_BIN", "").strip()
    if bindir:
        candidate = Path(bindir) / f"{name}.exe"
        if candidate.exists():
            return str(candidate)
        candidate = Path(bindir) / name
        if candidate.exists():
            return str(candidate)
    return shutil.which(name)


def run(cmd: list[str], log_name: str) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, errors="replace")
    out = proc.stdout.replace("\r\n", "\n")
    # Normalize vsim transcript prompts ("# PASS ..." -> "PASS ...") so markers
    # and diagnostics can be matched uniformly.
    normalized = "\n".join(
        line[2:] if line.startswith("# ") else ("" if line == "#" else line)
        for line in out.split("\n")
    )
    path = SIM_DIR / "logs" / log_name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(out, encoding="utf-8")
    return proc.returncode, normalized


class Driver:
    def __init__(self) -> None:
        self.failures: list[str] = []

    def check(self, name: str, marker: str | None, rc: int, out: str) -> None:
        problems = []
        if rc != 0:
            problems.append(f"exit code {rc}")
        if ERROR_RE.search(out):
            problems.append("error/fatal diagnostic present")
        # marker is a trusted constant regular expression anchored per line.
        if marker is not None and not re.search(rf"^{marker}\s*$", out, re.MULTILINE):
            problems.append(f"missing PASS marker '{marker}'")
        if problems:
            self.failures.append(f"{name}: {'; '.join(problems)}")
            print(f"FAIL {name} ({'; '.join(problems)})", flush=True)
        else:
            print(f"[ok] {name}", flush=True)

    def compile(self, vlog: str, library: str, files: list[str], defines: list[str]) -> None:
        cmd = [vlog, "-sv", "-quiet", "-work", str(SIM_DIR / library)] + files + [f"+define+{d}" for d in defines]
        rc, out = run(cmd, f"compile_{library}_{('_'.join(defines) or 'base')}.log")
        self.check(f"compile {library} {defines or 'base'}", None, rc, out)

    def simulate(self, vsim: str, library: str, top: str, name: str,
                 plusargs: list[str], marker: str,
                 search_libs: list[str] | None = None) -> None:
        do = "onerror {quit -f}; run -all; quit -f"
        cmd = [vsim, "-c", "-quiet", "-work", str(SIM_DIR / library), "-voptargs=+acc", top]
        for extra in search_libs or []:
            cmd += ["-L", str(SIM_DIR / extra)]
        cmd += ["-do", do] + plusargs
        rc, out = run(cmd, f"{name}.log")
        self.check(name, marker, rc, out)


def main() -> int:
    vlog, vsim = find_tool("vlog"), find_tool("vsim")
    vlib_tool = find_tool("vlib")
    if not vlog or not vsim or not vlib_tool:
        print("BLOCKED: ModelSim/Questasim (vlib + vlog + vsim) is not installed.", file=sys.stderr)
        return 2

    SIM_DIR.mkdir(parents=True, exist_ok=True)
    d = Driver()

    for lib in ("work_base", "work_250k"):
        libpath = SIM_DIR / lib
        if libpath.exists():
            shutil.rmtree(libpath)
        rc, _ = run([vlib_tool, str(libpath)], f"vlib_{lib}.log")
        if rc != 0:
            print(f"FAIL vlib {lib}", file=sys.stderr)
            return 2

    # Both libraries contain the full RTL; work_250k differs only in that its
    # rate-dependent testbenches are compiled with +define+RATE250.
    d.compile(vlog, "work_base", RTL_FILES + [f"tb/{t}.sv" for t in UNIT_TBS + RATE_TBS], [])
    d.compile(vlog, "work_250k", RTL_FILES + [f"tb/{t}.sv" for t in RATE_TBS], ["RATE250"])

    for tb in UNIT_TBS:
        d.simulate(vsim, "work_base", tb, tb, [], f"PASS {tb}")

    for rate, lib in (("1m", "work_base"), ("250k", "work_250k")):
        d.simulate(vsim, lib, "tb_css_phy_protocol", f"protocol_{rate}",
                   [], r"PASS tb_css_phy_protocol rate=[01] samples=\d+")
        for length in LENGTHS:
            payload = f"vectors/full_{rate}_len{length}_payload.hex"
            common = [f"+PLEN={length}", f"+PAYLOAD={payload}"]
            d.simulate(vsim, lib, "tb_css_tx_controller", f"controller_{rate}_len{length}",
                       common + [f"+CHIPS=vectors/full_{rate}_len{length}_chips.txt"],
                       rf"PASS tb_css_tx_controller rate=\d+ plen={length} chips=\d+")
            d.simulate(vsim, lib, "tb_css_phy_tx_top", f"top_{rate}_len{length}",
                       common + [f"+SAMPLES=vectors/full_{rate}_len{length}_samples.hex"],
                       rf"PASS tb_css_phy_tx_top rate=\d+ plen={length} chirp=\d+ sdiv=\d+ samples=\d+")
        # Back-to-back packets: equal length + distinct contents between
        # packets 1 and 2 detects cross-packet state leakage.
        multi_args = [
            "+P1LEN=25", f"+P1PAYLOAD=vectors/full_{rate}_len25_payload.hex",
            "+P2LEN=25", f"+P2PAYLOAD=vectors/full_{rate}_len25alt_payload.hex",
            "+P3LEN=127", f"+P3PAYLOAD=vectors/full_{rate}_len127alt_payload.hex",
            f"+P1SAMPLES=vectors/full_{rate}_len25_samples.hex",
            f"+P2SAMPLES=vectors/full_{rate}_len25alt_samples.hex",
            f"+P3SAMPLES=vectors/full_{rate}_len127alt_samples.hex",
        ]
        d.simulate(vsim, lib, "tb_css_phy_tx_multi", f"multi_{rate}", multi_args,
                   r"PASS tb_css_phy_tx_multi rate=\d+ packets=3 lens=\d+,\d+,\d+")

    # Chirp-index sweep: elaborations with CHIRP_INDEX=2..4 (1 is covered by
    # the canonical matrix). Each variant gets its own library holding only a
    # chirp-defined top testbench; the RTL resolves from work_base via -L.
    for rate in ("1m", "250k"):
        rate_defs = ["RATE250"] if rate == "250k" else []
        for m in (2, 3, 4):
            lib = f"work_{rate}_chirpm{m}"
            libpath = SIM_DIR / lib
            if libpath.exists():
                shutil.rmtree(libpath)
            rc, _ = run([vlib_tool, str(libpath)], f"vlib_{lib}.log")
            if rc != 0:
                print(f"FAIL vlib {lib}", file=sys.stderr)
                return 2
            d.compile(vlog, lib, [f"tb/tb_css_phy_tx_top.sv"], rate_defs + [f"CHIRP_M{m}"])
            d.simulate(vsim, lib, "tb_css_phy_tx_top", f"top_{rate}_chirpm{m}",
                       ["+PLEN=25", "+PAYLOAD=vectors/chirp_sweep_payload.hex",
                        f"+SAMPLES=vectors/full_{rate}_len25_chirpm{m}_samples.hex"],
                       rf"PASS tb_css_phy_tx_top rate=\d+ plen=25 chirp={m} sdiv=1 samples=\d+",
                       search_libs=["work_base"])

    # SAMPLE_DIV sweep: the output sample stream must be value-identical to
    # SAMPLE_DIV=1, only time-stretched; the same golden vectors therefore
    # validate the divider. div=2 exercises clog2()==1, div=5 a prime period.
    for rate in ("1m", "250k"):
        rate_defs = ["RATE250"] if rate == "250k" else []
        for div in (2, 5):
            lib = f"work_{rate}_sdiv{div}"
            libpath = SIM_DIR / lib
            if libpath.exists():
                shutil.rmtree(libpath)
            rc, _ = run([vlib_tool, str(libpath)], f"vlib_{lib}.log")
            if rc != 0:
                print(f"FAIL vlib {lib}", file=sys.stderr)
                return 2
            d.compile(vlog, lib, [f"tb/tb_css_phy_tx_top.sv"], rate_defs + [f"SAMPLE_DIV_{div}"])
            d.simulate(vsim, lib, "tb_css_phy_tx_top", f"top_{rate}_sdiv{div}",
                       ["+PLEN=25", f"+PAYLOAD=vectors/full_{rate}_len25_payload.hex",
                        f"+SAMPLES=vectors/full_{rate}_len25_samples.hex"],
                       rf"PASS tb_css_phy_tx_top rate=\d+ plen=25 chirp=\d+ sdiv={div} samples=\d+",
                       search_libs=["work_base"])

    total = 12 + 2 * (1 + 2 * len(LENGTHS) + 1) + 2 * 3 + 2 * 2
    if d.failures:
        print(f"\nRTL regression (ModelSim): {len(d.failures)} failure(s)")
        for f in d.failures:
            print(f"  - {f}")
        print("FAIL: complete RTL regression")
        return 1
    print("\nPASS: complete RTL regression "
          f"({total} simulations: {len(UNIT_TBS)} unit + 2 rates x (protocol + controller/top x {len(LENGTHS)} lengths))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
