#!/usr/bin/env python3
from pathlib import Path
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from css_reference import *

VECTORS = ROOT / "vectors"
RTL_ROM = ROOT / "rtl" / "rom"
REPORTS = ROOT / "reports"
VECTORS.mkdir(parents=True, exist_ok=True)
RTL_ROM.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)

for rate, name in [(RATE_1M, "codeword_1m.mem"), (RATE_250K, "codeword_250k.mem")]:
    table = codeword_table(rate)
    with (RTL_ROM / name).open("w", encoding="utf-8") as f:
        for row in table:
            f.write("".join("1" if x == 1 else "0" for x in row) + "\n")

for m in range(1, 5):
    fixed = chirp_sequence_fixed(m).reshape(-1, order="F")
    for comp, values in [("real", fixed.real), ("imag", fixed.imag)]:
        with (RTL_ROM / f"chirp_m{m}_{comp}.mem").open("w", encoding="utf-8") as f:
            for value in values.astype(int):
                f.write(twos_complement_binary(int(value), 6) + "\n")

with (VECTORS / "symbol_mapper_1m.txt").open("w", encoding="utf-8") as f:
    for sym, row in enumerate(codeword_table(RATE_1M)):
        f.write(f"{sym} " + "".join("1" if x == 1 else "0" for x in row) + "\n")
with (VECTORS / "symbol_mapper_250k.txt").open("w", encoding="utf-8") as f:
    for sym, row in enumerate(codeword_table(RATE_250K)):
        f.write(f"{sym} " + "".join("1" if x == 1 else "0" for x in row) + "\n")

with (VECTORS / "interleaver_250k_indices.txt").open("w", encoding="utf-8") as f:
    for out_idx, in_idx in enumerate(INTERLEAVER_PERM):
        f.write(f"{out_idx} {int(in_idx)}\n")

with (VECTORS / "qpsk_table.txt").open("w", encoding="utf-8") as f:
    f.write("I Q REAL IMAG\n")
    for i in (-1, 1):
        for q in (-1, 1):
            y = qpsk_map(np.array([i]), np.array([q]))[0]
            f.write(f"{i} {q} {int(y.real)} {int(y.imag)}\n")

stim_i = np.array([1,-1,1,1,-1,-1,1,-1, 1,1,-1,1,-1,1,-1,-1], dtype=np.int8)
stim_q = np.array([1,1,-1,1,-1,1,-1,-1, -1,1,1,-1,1,-1,-1,1], dtype=np.int8)
dq = dqpsk_encode(qpsk_map(stim_i, stim_q))
with (VECTORS / "dqpsk_unit.txt").open("w", encoding="utf-8") as f:
    f.write("IDX I Q OUT_REAL OUT_IMAG\n")
    for n, (i,q,y) in enumerate(zip(stim_i, stim_q, dq)):
        f.write(f"{n} {int(i)} {int(q)} {int(y.real)} {int(y.imag)}\n")

unit_dq = np.array([1+1j, 1-1j, -1+1j, -1-1j, -1+1j, 1+1j, 1-1j, -1-1j], dtype=np.complex128)
unit_csk = csk_modulate(unit_dq, 1)
with (VECTORS / "csk_m1_two_groups.hex").open("w", encoding="utf-8") as f:
    for v in unit_csk:
        f.write(f"{int(v.real)&0xFF:02x} {int(v.imag)&0xFF:02x}\n")
with (VECTORS / "csk_m1_two_groups_symbols.txt").open("w", encoding="utf-8") as f:
    for g in range(2):
        vals = unit_dq[g*4:g*4+4]
        f.write(str(g))
        for v in vals:
            f.write(f" {int(v.real)} {int(v.imag)}")
        f.write("\n")

manifest = []
for rate, rate_name in [(RATE_1M, "1m"), (RATE_250K, "250k")]:
    for length in (0, 1, 3, 25, 127):
        payload = deterministic_payload(length)
        result = transmit(payload, rate, chirp_index=1)
        base = f"full_{rate_name}_len{length}"
        (VECTORS / f"{base}_payload.hex").write_text("\n".join(f"{b:02x}" for b in payload)+("\n" if payload else ""), encoding="utf-8")
        with (VECTORS / f"{base}_chips.txt").open("w", encoding="utf-8") as f:
            for ci, cq in zip(result.i_chips, result.q_chips):
                f.write(f"{1 if int(ci)==1 else 0} {1 if int(cq)==1 else 0}\n")
        write_complex_samples(VECTORS / f"{base}_samples.txt", result.samples, 8)
        with (VECTORS / f"{base}_samples.hex").open("w", encoding="utf-8") as f:
            for v in result.samples:
                r = int(round(float(v.real))) & 0xFF
                i = int(round(float(v.imag))) & 0xFF
                f.write(f"{r:02x} {i:02x}\n")
        manifest.append((rate_name, length, len(result.i_chips), len(result.dqpsk), len(result.samples), padding_count(length, rate)))

with (VECTORS / "MANIFEST.txt").open("w", encoding="utf-8") as f:
    f.write("RATE PAYLOAD_BYTES QPSK_SYMBOLS DQPSK_SYMBOLS OUTPUT_SAMPLES PAD_BITS\n")
    for row in manifest:
        f.write("%s %d %d %d %d %d\n" % row)

print(f"Generated vectors and ROMs under {ROOT}")
