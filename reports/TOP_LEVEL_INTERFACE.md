# Top-Level Interface Audit

Actual final top module: `rtl/css_tx_top.v` (HEAD of this release branch).

## Implemented ports

| Port | Dir | Width | Meaning / range |
|---|---|---|---|
| `clk` | IN | 1 | System clock. One output sample per clock while `o_valid`. |
| `rst_n` | IN | 1 | **Asynchronous, active-low** reset (all FSMs/counters). Note: assignment Table 3-1 specifies a *synchronous* reset; the RTL uses async low. Behavior verified for both power-on and mid-packet reset. |
| `start` | IN | 1 | One-cycle pulse initiating transmission. Equivalent of assignment `start_Tx`. Sampled in `ST_IDLE`; latched config is `data_rate`, `chirp_index`, `payload_len`. |
| `data_rate` | IN | 1 | 0 = 1 Mb/s, 1 = 250 kb/s (assignment table has no such port; required to cover both rates). |
| `chirp_index` | IN | 2 | Chirp sequence m = chirp_index+1 (m = 1..4 per IEEE 802.15.4a). |
| `payload_len` | IN | 7 | Payload length in bytes, 0..127. Verified end-to-end at 0, 1, 3, 20, 25, 40, 55 and 127 bytes; PHR encodes 7-bit length LSB-first per reference. Assignment's `payloadLength` is 8 bits wide but length <= 127 makes 7 bits sufficient. |
| `payload_ready` | OUT | 1 | Payload RAM write enable (`!busy`). Bytes are streamed into the RAM **before** `start`. |
| `payload_valid` | IN | 1 | Handshake: with `payload_ready`, one byte is written per clock. |
| `payload_data` | IN | 8 | Payload byte (assignment `payload_din`). Addressing is implicit FIFO order (`wr_ptr`) rather than an explicit address port; equivalent pre-start preload semantics as in reference Figure 3-3. |
| `o_i`, `o_q` | OUT | 7 signed each | Complex baseband sample (real/imag). Equivalent of assignment `Tx_real`/`Tx_imag` (7-bit signed vs 8-bit declared there; values fit since max magnitude is 62 from 31*2 products... bounded by coefficient set {0,±1} x 6-bit -> <= 62, fits in 7-bit signed). |
| `o_valid` | OUT | 1 | Asserted on every valid output sample. |
| `o_sop` / `o_eop` | OUT | 1 | Start/end of packet markers. Together with `busy` falling they provide the `done_Tx` semantics (eop marks the last zero sample of the closing gap; see Defect report D-1 for a control-flow caveat on `busy`). |

## Comparison against assignment interface (reference/CSS_PHY_Transmitter_Project.docx, Section 5)

| Assignment signal | RTL equivalent | Status |
|---|---|---|
| clk | clk | match |
| reset (sync) | rst_n (async low) | deviation documented above |
| start_Tx | start | match (renamed) |
| payloadLength[7:0] | payload_len[6:0] | width reduced, range identical (<=127) |
| payload_din/addr | payload_valid/data + internal wr_ptr | functionally equivalent preload model |
| done_Tx | o_eop + busy deassertion | see D-1 defect (busy does not deassert) |
| Tx_real/Tx_imag[7:0] | o_i/o_q[6:0] signed + o_valid | equivalent data, extra handshake |

Interface definitions were NOT changed in this release session.
