#!/usr/bin/env python3
from pathlib import Path
import random
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
    with (RTL_ROM / name).open("w", newline="\n", encoding="utf-8") as f:
        for row in table:
            f.write("".join("1" if x == 1 else "0" for x in row) + "\n")

for m in range(1, 5):
    fixed = chirp_sequence_fixed(m).reshape(-1, order="F")
    for comp, values in [("real", fixed.real), ("imag", fixed.imag)]:
        with (RTL_ROM / f"chirp_m{m}_{comp}.mem").open("w", newline="\n", encoding="utf-8") as f:
            for value in values.astype(int):
                f.write(twos_complement_binary(int(value), 6) + "\n")

with (VECTORS / "symbol_mapper_1m.txt").open("w", newline="\n", encoding="utf-8") as f:
    for sym, row in enumerate(codeword_table(RATE_1M)):
        f.write(f"{sym} " + "".join("1" if x == 1 else "0" for x in row) + "\n")
with (VECTORS / "symbol_mapper_250k.txt").open("w", newline="\n", encoding="utf-8") as f:
    for sym, row in enumerate(codeword_table(RATE_250K)):
        f.write(f"{sym} " + "".join("1" if x == 1 else "0" for x in row) + "\n")

with (VECTORS / "interleaver_250k_indices.txt").open("w", newline="\n", encoding="utf-8") as f:
    for out_idx, in_idx in enumerate(INTERLEAVER_PERM):
        f.write(f"{out_idx} {int(in_idx)}\n")

with (VECTORS / "qpsk_table.txt").open("w", newline="\n", encoding="utf-8") as f:
    f.write("I Q REAL IMAG\n")
    for i in (-1, 1):
        for q in (-1, 1):
            y = qpsk_map(np.array([i]), np.array([q]))[0]
            f.write(f"{i} {q} {int(y.real)} {int(y.imag)}\n")

stim_i = np.array([1,-1,1,1,-1,-1,1,-1, 1,1,-1,1,-1,1,-1,-1], dtype=np.int8)
stim_q = np.array([1,1,-1,1,-1,1,-1,-1, -1,1,1,-1,1,-1,-1,1], dtype=np.int8)

# ---------------------------------------------------------------------------
# Exhaustive DQPSK transition stimulus.
#
# The encoder is a rotating 4-tap complex delay line: out[n] = in[n]*fb[n%4],
# fb[k] <- out when phase==k, with all lanes initialised to 1+1j at packet
# start. QPSK inputs act as rotations on each lane's feedback value:
#   (1,0): identity; (0,1): +90 deg; (0,-1): -90 deg; (-1,0): 180 deg.
# Starting from (1,1) every lane therefore stays inside S = {+-1 +-1j} after
# the first symbol, giving exactly 4 reachable feedback states x 4 inputs
# = 16 differential transitions, plus the 4 initial-state multiplies against
# the un-normalised 1+1j seed. The schedule below visits every one of those
# 20 products and asserts completeness here so the vector can never silently
# regress to partial coverage.
# ---------------------------------------------------------------------------
# Valid QPSK chip pairs in the +-1 stimulus convention used by the vector
# files (the RTL testbench maps them to bits via vi==1). Each maps to one
# axis-unit symbol through qpsk_map and therefore acts on each lane's
# feedback value as a pure rotation:
#   ( 1, 1) -> +1 : identity;        (-1, 1) -> +j : (a,b) -> (-b,a)
#   ( 1,-1) -> -j : (a,b) -> (b,-a); (-1,-1) -> -1 : (a,b) -> (-a,-b)
_QPSK_SYMBOLS = [(1, 1), (-1, 1), (1, -1), (-1, -1)]
_ROTATION = {(1, 1): lambda p: p,
             (-1, 1): lambda p: (-p[1], p[0]),
             (1, -1): lambda p: (p[1], -p[0]),
             (-1, -1): lambda p: (-p[0], -p[1])}
_STATES = [(1, 1), (-1, 1), (-1, -1), (1, -1)]  # order reached by repeated (-1,1)


def dqpsk_exhaustive_symbols() -> tuple[list, set]:
    """Build a symbol stream covering initial-state x4 and state x input x16.

    Returns the flat QPSK symbol list and the visited (feedback_state, input)
    pair set. Raises AssertionError if coverage is incomplete."""
    groups: list = []
    visited: set = set()
    # Segment 1: initial feedback seed (1+1j) multiplied by each input.
    for sym in _QPSK_SYMBOLS:
        groups.append([sym] * 4)
        visited.add(((1, 1), sym))
    # Segment 2: every steady-state feedback value driven by every input.
    # All lanes receive identical symbols, so they remain value-aligned and a
    # single scalar tracks the common feedback state.
    def advance(sym) -> int:
        rotated = _ROTATION[sym](_STATES[0])
        return (_STATES.index(rotated)) % 4

    state_idx = 0
    for s in range(4):
        groups.extend([[(-1, 1)] * 4] * ((s - state_idx) % 4))  # rotate to state s
        state_idx = s
        for sym in _QPSK_SYMBOLS:
            groups.append([sym] * 4)
            visited.add((_STATES[s], sym))
            back = (-advance(sym)) % 4  # re-align lanes onto feedback state s
            groups.extend([[(-1, 1)] * 4] * back)
            state_idx = s
    symbols = [sym for group in groups for sym in group]
    expected = {(_STATES[s], sym) for s in range(4) for sym in _QPSK_SYMBOLS} | {((1, 1), sym) for sym in _QPSK_SYMBOLS}
    assert visited == expected, f"DQPSK stimulus coverage incomplete: missing {expected - visited}"
    return symbols, visited


dq_exhaustive_syms, dq_exhaustive_pairs = dqpsk_exhaustive_symbols()
stim_e = np.array(dq_exhaustive_syms, dtype=np.int8)
dq = dqpsk_encode(qpsk_map(stim_i, stim_q))
with (VECTORS / "dqpsk_unit.txt").open("w", newline="\n", encoding="utf-8") as f:
    f.write("IDX I Q OUT_REAL OUT_IMAG\n")
    f.write(f"{len(stim_i)}\n")
    for n, (i,q,y) in enumerate(zip(stim_i, stim_q, dq)):
        f.write(f"{n} {int(i)} {int(q)} {int(y.real)} {int(y.imag)}\n")

dq_full = dqpsk_encode(qpsk_map(stim_e[:, 0], stim_e[:, 1]))
with (VECTORS / "dqpsk_transitions.txt").open("w", newline="\n", encoding="utf-8") as f:
    f.write("IDX I Q OUT_REAL OUT_IMAG\n")
    f.write(f"{len(dq_full)}\n")
    for n, (i,q,y) in enumerate(zip(stim_e[:, 0], stim_e[:, 1], dq_full)):
        f.write(f"{n} {int(i)} {int(q)} {int(y.real)} {int(y.imag)}\n")

unit_dq = np.array([1+1j, 1-1j, -1+1j, -1-1j, -1+1j, 1+1j, 1-1j, -1-1j], dtype=np.complex128)
unit_csk = csk_modulate(unit_dq, 1)
with (VECTORS / "csk_m1_two_groups.hex").open("w", newline="\n", encoding="utf-8") as f:
    for v in unit_csk:
        f.write(f"{int(v.real)&0xFF:02x} {int(v.imag)&0xFF:02x}\n")
with (VECTORS / "csk_m1_two_groups_symbols.txt").open("w", newline="\n", encoding="utf-8") as f:
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
        (VECTORS / f"{base}_payload.hex").write_text("\n".join(f"{b:02x}" for b in payload)+("\n" if payload else ""), newline="\n", encoding="utf-8")
        with (VECTORS / f"{base}_chips.txt").open("w", newline="\n", encoding="utf-8") as f:
            for ci, cq in zip(result.i_chips, result.q_chips):
                f.write(f"{1 if int(ci)==1 else 0} {1 if int(cq)==1 else 0}\n")
        write_complex_samples(VECTORS / f"{base}_samples.txt", result.samples, 8)
        with (VECTORS / f"{base}_samples.hex").open("w", newline="\n", encoding="utf-8") as f:
            for v in result.samples:
                r = int(round(float(v.real))) & 0xFF
                i = int(round(float(v.imag))) & 0xFF
                f.write(f"{r:02x} {i:02x}\n")
        manifest.append((rate_name, length, len(result.i_chips), len(result.dqpsk), len(result.samples), padding_count(length, rate)))

with (VECTORS / "MANIFEST.txt").open("w", newline="\n", encoding="utf-8") as f:
    f.write("RATE PAYLOAD_BYTES QPSK_SYMBOLS DQPSK_SYMBOLS OUTPUT_SAMPLES PAD_BITS\n")
    for row in manifest:
        f.write("%s %d %d %d %d %d\n" % row)

# Back-to-back multi-packet vectors: equal length, distinct contents, so a
# stale payload/framing/modulator state between packets breaks equality.
for rate, rate_name in [(RATE_1M, "1m"), (RATE_250K, "250k")]:
    for length in (25, 127):
        payload = alternate_payload(length)
        result = transmit(payload, rate, chirp_index=1)
        base = f"full_{rate_name}_len{length}alt"
        (VECTORS / f"{base}_payload.hex").write_text("\n".join(f"{b:02x}" for b in payload)+("\n" if payload else ""), newline="\n", encoding="utf-8")
        with (VECTORS / f"{base}_samples.hex").open("w", newline="\n", encoding="utf-8") as f:
            for v in result.samples:
                r = int(round(float(v.real))) & 0xFF
                i = int(round(float(v.imag))) & 0xFF
                f.write(f"{r:02x} {i:02x}\n")

# Chirp-index sweep vectors: the canonical matrix covers CHIRP_INDEX=1; these
# exercise the full chain for chirps 2..4 (ROM selection + per-chirp gaps).
payload25 = deterministic_payload(25)
(VECTORS / "chirp_sweep_payload.hex").write_text(
    "\n".join(f"{b:02x}" for b in payload25) + "\n", newline="\n", encoding="utf-8")
for rate, rate_name in [(RATE_1M, "1m"), (RATE_250K, "250k")]:
    for m in (2, 3, 4):
        result = transmit(payload25, rate, chirp_index=m)
        base = f"full_{rate_name}_len25_chirpm{m}"
        with (VECTORS / f"{base}_samples.hex").open("w", newline="\n", encoding="utf-8") as f:
            for v in result.samples:
                r = int(round(float(v.real))) & 0xFF
                i = int(round(float(v.imag))) & 0xFF
                f.write(f"{r:02x} {i:02x}\n")


# ---------------------------------------------------------------------------
# Deterministic multi-packet stress schedules.
#
# Two independent fixed seeds:
#   * STRESS_SEED_CI  : compact schedule (default) executed by make rtl /
#                       make rtl-msim and required by the CI evidence gate.
#   * STRESS_SEED_EXT : extended local stress (120 packets) for soak runs;
#                       selectable via +SCHEDULE= without touching CI time.
# Packet streams deliberately include length corners (0, 1, and the 63/64
# word-boundary pair), zero-gap back-to-back starts, and varied idle gaps so
# sequence-dependent state leakage breaks golden equality.
# ---------------------------------------------------------------------------
STRESS_SEED_CI = 0xC5C5C5A5
STRESS_SEED_EXT = 0xE717E51D


def stress_lengths(rng: random.Random, count: int) -> list:
    lengths = [0, 1]
    lengths += [rng.randrange(2, 63) for _ in range(count - 4)]
    lengths += [63, 64]
    return lengths


def emit_stress_schedule(rate: int, rate_name: str, seed: int, count: int) -> None:
    rng = random.Random(seed)
    index_lines = []
    for pkt, length in enumerate(stress_lengths(rng, count)):
        payload = bytes(rng.randrange(256) for _ in range(length))
        gap = rng.choice([0, 0, 1, 2, 3, 5, 8, 13])
        pbase = f"stress_{rate_name}_p{pkt}"
        (VECTORS / f"{pbase}_payload.hex").write_text(
            "\n".join(f"{b:02x}" for b in payload) + ("\n" if payload else ""),
            encoding="utf-8")
        result = transmit(payload, rate, chirp_index=1)
        with (VECTORS / f"{pbase}_samples.hex").open("w", newline="\n", encoding="utf-8") as f:
            for v in result.samples:
                r = int(round(float(v.real))) & 0xFF
                i = int(round(float(v.imag))) & 0xFF
                f.write(f"{r:02x} {i:02x}\n")
        # Numeric-only columns: the testbench derives file names from the
        # packet id and a rate tag plusarg, avoiding $fscanf("%s") which is
        # not portable across simulators.
        index_lines.append(f"{pkt} {length} {gap}")
    (VECTORS / f"stress_{rate_name}_index.txt").write_text(
        "\n".join(index_lines) + "\n", newline="\n", encoding="utf-8")
    print(f"stress schedule {rate_name}: seed=0x{seed:X} packets={count}")


emit_stress_schedule(RATE_1M, "1m", STRESS_SEED_CI, count=24)
emit_stress_schedule(RATE_250K, "250k", STRESS_SEED_CI, count=24)
emit_stress_schedule(RATE_1M, "1m_ext", STRESS_SEED_EXT, count=120)
emit_stress_schedule(RATE_250K, "250k_ext", STRESS_SEED_EXT, count=120)

print(f"Generated vectors and ROMs under {ROOT}")
