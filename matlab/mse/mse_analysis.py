#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "matlab" / "vector_generation"
sys.path.insert(0, str(REF))
from css_reference import chirp_mse

REPORTS = ROOT / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)
out = REPORTS / "mse_results.csv"
with out.open("w", encoding="utf-8") as f:
    f.write("bits,round_mse,floor_mse,round_pass_0p005,floor_pass_0p005\n")
    for bits in range(2, 9):
        r = chirp_mse(1, bits, "round")
        fl = chirp_mse(1, bits, "floor")
        f.write(f"{bits},{r:.12g},{fl:.12g},{str(r<0.005).lower()},{str(fl<0.005).lower()}\n")
        print(bits, f"round={r:.9g}", f"floor={fl:.9g}")

all_out = REPORTS / "mse_all_chirps.csv"
with all_out.open("w", encoding="utf-8") as f:
    f.write("chirp_index,bits,floor_mse,pass_0p005\n")
    for m in range(1, 5):
        for bits in range(2, 9):
            fl = chirp_mse(m, bits, "floor")
            f.write(f"{m},{bits},{fl:.12g},{str(fl<0.005).lower()}\n")
print(out)
print(all_out)
