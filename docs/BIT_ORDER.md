# Bit-Ordering Contract

The supplied MATLAB transmitter is authoritative for bit/data ordering. The RTL preserves these boundaries explicitly.

| Boundary | Required order |
|---|---|
| Payload byte → serial bits | LSB first: bit 0 through bit 7 |
| PHR payload length | length bit 0 through bit 6, then five zero bits |
| PHR + PSDU | PHR first, payload second, padding last |
| DEMUX | first serial bit → I, second → Q, alternating |
| Serial path bits → symbol address | first collected bit is symbol MSB |
| Mapper codeword → chip stream | c0 first |
| 250-kbps interleaver | G0,G13,G2,G15,G4,G9,G6,G11,G8,G5,G10,G7,G12,G1,G14,G3 |
| Preamble/SFD | preamble first; SFD bit 0 first |
| QPSK | `(I,Q)` mapping follows the MATLAB equation exactly |
| DQPSK | four feedback phases; stream order unchanged |
| DQPSK group → subchirps | symbols n..n+3 multiply k=0..3 respectively |
| Chirp samples | 38 samples per subchirp, k=0..3, then explicit zero gap |
| Final I/Q | signed two's-complement 8-bit sample values |

## Directed anti-reversal patterns

The regression uses asymmetric values specifically to expose accidental reversal:

- `8'h01` → `1,0,0,0,0,0,0,0`
- `8'h80` → `0,0,0,0,0,0,0,1`
- `8'h96` → `0,1,1,0,1,0,0,1`
- `8'hA5` → `1,0,1,0,0,1,0,1`
- `8'h3C` → `0,0,1,1,1,1,0,0`

`tests/test_bit_order.py` checks these boundaries directly for both PHY rates. `tests/test_randomized.py` extends the check with deterministic seed `0x802154`.
