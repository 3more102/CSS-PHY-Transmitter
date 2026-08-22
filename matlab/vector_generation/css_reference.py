#!/usr/bin/env python3
"""Executable reference model derived from the supplied MATLAB CSS transmitter.

The implementation intentionally preserves the supplied MATLAB behaviors that
matter for RTL equivalence, including:
  * PHR payload length transmitted LSB-first;
  * MATLAB padding formula N - mod(length, N), which adds a full block when
    the unpadded length is already an exact multiple;
  * first demux bit to I, second to Q;
  * first bit of each data symbol as the MSB of the codeword ROM address;
  * c0 transmitted before c1...;
  * exact 250-kbps 64-chip interleaver permutation;
  * fixed-point transmitter chirp quantization by floor at 6 signed bits;
  * unnormalized DQPSK feedback initialized to 1+j;
  * zero-valued samples during Teven/Todd gaps.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence
import math
import numpy as np

RATE_1M = 0
RATE_250K = 1
PHR_LENGTH = 12
SFD_LENGTH = 16
SAMPLE_FREQ_MHZ = 32
TSUB = 38
TCHIRP_AVG = 192
TX_DAC_BITS = 6

SFD = {
    RATE_1M: np.array([-1, 1, 1, 1, -1, 1, -1, -1, 1, -1, -1, 1, 1, 1, -1, -1], dtype=np.int8),
    RATE_250K: np.array([-1, 1, 1, 1, 1, -1, 1, -1, -1, -1, 1, -1, -1, -1, 1, 1], dtype=np.int8),
}
PREAMBLE_LENGTH = {RATE_1M: 32, RATE_250K: 80}
CODEWORD_LENGTH = {RATE_1M: 4, RATE_250K: 32}
BITS_PER_SYMBOL = {RATE_1M: 3, RATE_250K: 6}
PAD_MODULUS = {RATE_1M: 6, RATE_250K: 24}

INTERLEAVER_PERM = np.array([
    0,1,2,3,52,53,54,55,8,9,10,11,60,61,62,63,
    16,17,18,19,36,37,38,39,24,25,26,27,44,45,46,47,
    32,33,34,35,20,21,22,23,40,41,42,43,28,29,30,31,
    48,49,50,51,4,5,6,7,56,57,58,59,12,13,14,15,
], dtype=np.int64)

ZETA_K_M = np.array([
    [1, 1, -1, -1],
    [1, -1, 1, -1],
    [-1, -1, 1, 1],
    [-1, 1, -1, 1],
], dtype=np.float64).T
F_MHZ_K_M = np.array([
    [-3.15, +3.15, +3.15, -3.15],
    [+3.15, -3.15, -3.15, +3.15],
    [-3.15, +3.15, +3.15, -3.15],
    [+3.15, -3.15, -3.15, +3.15],
], dtype=np.float64).T


def hadamard(n: int) -> np.ndarray:
    if n < 1 or (n & (n - 1)):
        raise ValueError("n must be a positive power of two")
    h = np.array([[1]], dtype=np.int8)
    while h.shape[0] < n:
        h = np.block([[h, h], [h, -h]])
    return h


def codeword_table(rate: int) -> np.ndarray:
    n = CODEWORD_LENGTH[rate]
    h = hadamard(n)
    return np.vstack([h, -h]).astype(np.int8)


def phr_bits(payload_length: int) -> np.ndarray:
    if not 0 <= payload_length <= 127:
        raise ValueError("payload_length must be in 0..127")
    length_bits = [(payload_length >> i) & 1 for i in range(7)]
    return np.array(length_bits + [0, 0, 0, 0, 0], dtype=np.int8)


def payload_to_bits(payload: bytes | Sequence[int]) -> np.ndarray:
    values = bytes(payload)
    return np.array([(b >> i) & 1 for b in values for i in range(8)], dtype=np.int8)


def padding_count(payload_length: int, rate: int) -> int:
    n = PAD_MODULUS[rate]
    return n - ((payload_length * 8 + PHR_LENGTH) % n)


def framed_binary_data(payload: bytes | Sequence[int], rate: int) -> np.ndarray:
    p = bytes(payload)
    bits = np.concatenate([phr_bits(len(p)), payload_to_bits(p)])
    return np.concatenate([bits, np.zeros(padding_count(len(p), rate), dtype=np.int8)])


def demux_iq(bits: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return bits[0::2].copy(), bits[1::2].copy()


def serial_to_symbols(path_bits: np.ndarray, rate: int) -> np.ndarray:
    n = BITS_PER_SYMBOL[rate]
    if len(path_bits) % n:
        raise ValueError("path length is not divisible by symbol width")
    rows = path_bits.reshape((-1, n))
    weights = 2 ** np.arange(n - 1, -1, -1)
    return (rows * weights).sum(axis=1).astype(np.int64)


def map_symbols(symbols: np.ndarray, rate: int) -> np.ndarray:
    return codeword_table(rate)[symbols]


def interleave_250k(words: np.ndarray) -> np.ndarray:
    if words.ndim != 2 or words.shape[1] != 32 or words.shape[0] % 2:
        raise ValueError("250-kbps interleaver requires an even number of 32-chip codewords")
    pairs = words.reshape((-1, 2, 32)).reshape((-1, 64))
    return pairs[:, INTERLEAVER_PERM]


def encoded_path_chips(path_bits: np.ndarray, rate: int) -> np.ndarray:
    words = map_symbols(serial_to_symbols(path_bits, rate), rate)
    if rate == RATE_1M:
        return words.reshape(-1)
    return interleave_250k(words).reshape(-1)


def ppdu_iq_chips(payload: bytes | Sequence[int], rate: int) -> tuple[np.ndarray, np.ndarray]:
    data = framed_binary_data(payload, rate)
    i_bits, q_bits = demux_iq(data)
    i_data = encoded_path_chips(i_bits, rate)
    q_data = encoded_path_chips(q_bits, rate)
    pre_sfd = np.concatenate([np.ones(PREAMBLE_LENGTH[rate], dtype=np.int8), SFD[rate]])
    return np.concatenate([pre_sfd, i_data]), np.concatenate([pre_sfd, q_data])


def qpsk_map(i_chips: np.ndarray, q_chips: np.ndarray) -> np.ndarray:
    i = np.asarray(i_chips, dtype=np.int16)
    q = np.asarray(q_chips, dtype=np.int16)
    if i.shape != q.shape:
        raise ValueError("I and Q paths must have equal lengths")
    return ((i + q) - 1j * (i - q)) / 2


def dqpsk_encode(qpsk: np.ndarray) -> np.ndarray:
    x = np.asarray(qpsk, dtype=np.complex128)
    if len(x) % 4:
        raise ValueError("DQPSK input count must be divisible by four")
    feedback = np.ones(4, dtype=np.complex128) + 1j * np.ones(4, dtype=np.complex128)
    out = np.empty_like(x)
    for i in range(0, len(x), 4):
        out[i:i+4] = x[i:i+4] * feedback
        feedback = out[i:i+4].copy()
    return out


def raised_cosine(t_sub: int = TSUB) -> np.ndarray:
    num_ones = 1 + math.floor(0.3 * t_sub)
    flat = np.ones(num_ones, dtype=np.float64)
    num_roll = int(t_sub / 2 - num_ones)
    n = np.arange(num_ones, num_ones + num_roll + 1)
    roll_down = 0.5 * (1 + np.cos(5 * np.pi / t_sub * (n - 0.3 * t_sub)))
    tmp = np.concatenate([flat, roll_down])
    return np.concatenate([tmp[::-1], tmp[1:int(t_sub / 2)]])


def chirp_sequence_float(chirp_index: int, sampling_freq_mhz: int = SAMPLE_FREQ_MHZ) -> np.ndarray:
    if chirp_index not in (1, 2, 3, 4):
        raise ValueError("chirp_index must be 1..4")
    t_sub = int(round(1.1875 * sampling_freq_mhz))
    time = np.arange(-t_sub / 2, t_sub / 2)
    window = raised_cosine(t_sub)
    out = np.zeros((t_sub, 4), dtype=np.complex128)
    m = chirp_index - 1
    for k in range(4):
        phase = 2 * np.pi / sampling_freq_mhz * (F_MHZ_K_M[k, m] + 7.3158 * ZETA_K_M[k, m] / (2 * sampling_freq_mhz) * time) * time
        out[:, k] = np.exp(1j * phase) * window
    return out


def quantize_complex_floor(values: np.ndarray, bits: int) -> np.ndarray:
    scale = (2 ** (bits - 1)) - 1
    return np.floor(values.real * scale) + 1j * np.floor(values.imag * scale)


def chirp_sequence_fixed(chirp_index: int, bits: int = TX_DAC_BITS) -> np.ndarray:
    return quantize_complex_floor(chirp_sequence_float(chirp_index), bits)


def gap_samples(chirp_index: int, odd: bool) -> int:
    even = [10, 20, 30, 40][chirp_index - 1]
    odd_gap = [70, 60, 50, 40][chirp_index - 1]
    return odd_gap if odd else even


def csk_modulate(dqpsk: np.ndarray, chirp_index: int, dac_bits: int = TX_DAC_BITS) -> np.ndarray:
    symbols = np.asarray(dqpsk, dtype=np.complex128)
    if len(symbols) % 4:
        raise ValueError("CSK requires groups of four DQPSK symbols")
    chirp = chirp_sequence_fixed(chirp_index, dac_bits)
    chunks: list[np.ndarray] = []
    for group_idx in range(len(symbols) // 4):
        group = symbols[group_idx*4:group_idx*4+4]
        active = (chirp * np.tile(group, (TSUB, 1))).reshape(-1, order="F")
        gap = np.zeros(gap_samples(chirp_index, odd=bool(group_idx & 1)), dtype=np.complex128)
        chunks.extend([active, gap])
    return np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.complex128)


@dataclass(frozen=True)
class TxResult:
    rate: int
    payload: bytes
    chirp_index: int
    framed_bits: np.ndarray
    i_chips: np.ndarray
    q_chips: np.ndarray
    qpsk: np.ndarray
    dqpsk: np.ndarray
    samples: np.ndarray


def transmit(payload: bytes | Sequence[int], rate: int, chirp_index: int = 1, dac_bits: int = TX_DAC_BITS) -> TxResult:
    p = bytes(payload)
    framed = framed_binary_data(p, rate)
    i_chips, q_chips = ppdu_iq_chips(p, rate)
    qpsk = qpsk_map(i_chips, q_chips)
    dqpsk = dqpsk_encode(qpsk)
    samples = csk_modulate(dqpsk, chirp_index, dac_bits)
    return TxResult(rate, p, chirp_index, framed, i_chips, q_chips, qpsk, dqpsk, samples)


def normalized_mse(exact: np.ndarray, fixed: np.ndarray) -> float:
    exact = np.asarray(exact, dtype=np.complex128)
    fixed = np.asarray(fixed, dtype=np.complex128)
    if exact.shape != fixed.shape:
        raise ValueError("MSE arrays must have same shape")
    denominator = np.sum(np.abs(exact) ** 2)
    if denominator == 0:
        return 0.0 if np.all(fixed == 0) else math.inf
    return float(np.sum(np.abs(exact - fixed) ** 2) / denominator)


def chirp_mse(chirp_index: int, bits: int, mode: str = "floor") -> float:
    floating = chirp_sequence_float(chirp_index).reshape(-1, order="F")
    scale = (2 ** (bits - 1)) - 1
    exact = floating * scale
    if mode == "floor":
        fixed = np.floor(exact.real) + 1j * np.floor(exact.imag)
    elif mode == "round":
        fixed = np.round(exact.real) + 1j * np.round(exact.imag)
    else:
        raise ValueError("mode must be 'floor' or 'round'")
    return normalized_mse(exact, fixed)


def twos_complement_binary(value: int, width: int) -> str:
    return format(value & ((1 << width) - 1), f"0{width}b")


def write_complex_samples(path: Path, samples: np.ndarray, width: int = 8) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for idx, v in enumerate(samples):
            r = int(round(float(v.real)))
            i = int(round(float(v.imag)))
            f.write(f"{idx} {r} {i} {twos_complement_binary(r,width)} {twos_complement_binary(i,width)}\n")


def deterministic_payload(length: int) -> bytes:
    return bytes(((37 * i + 0x35) ^ (i >> 1)) & 0xFF for i in range(length))
