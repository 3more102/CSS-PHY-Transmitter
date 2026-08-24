#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if ! command -v iverilog >/dev/null 2>&1 || ! command -v vvp >/dev/null 2>&1; then
  echo "BLOCKED: Icarus Verilog (iverilog + vvp) is not installed." >&2
  exit 2
fi
mkdir -p results/sim
RTL=(
  rtl/css_phy_pkg.sv rtl/payload_ram.sv rtl/phr_generator.sv rtl/zero_pad_framer.sv rtl/iq_demux.sv
  rtl/symbol_mapper_1m.sv rtl/symbol_mapper_250k.sv rtl/bit_interleaver.sv rtl/preamble_sfd_rom.sv
  rtl/qpsk_mapper.sv rtl/dqpsk_encoder.sv rtl/chirp_rom.sv rtl/csk_modulator.sv rtl/css_tx_controller.sv rtl/css_phy_tx_top.sv
)
run_tb() {
  local tb=$1; shift
  echo "== $tb =="
  iverilog -g2012 -Wall -s "$tb" -o "results/sim/$tb.vvp" "${RTL[@]}" "tb/$tb.sv" "$@"
  vvp "results/sim/$tb.vvp"
}
run_tb tb_payload_ram
run_tb tb_phr_generator
run_tb tb_zero_pad_framer
run_tb tb_iq_demux
run_tb tb_preamble_sfd_rom
run_tb tb_symbol_mapper_1m
run_tb tb_symbol_mapper_250k
run_tb tb_interleaver
run_tb tb_qpsk_mapper
run_tb tb_dqpsk_encoder
run_tb tb_chirp_rom
run_tb tb_csk_modulator

for rate in 1m 250k; do
  defs=()
  [[ $rate == 250k ]] && defs=(-DRATE250)
  iverilog -g2012 -Wall "${defs[@]}" -s tb_css_tx_controller -o "results/sim/controller_${rate}.vvp" "${RTL[@]}" tb/tb_css_tx_controller.sv
  iverilog -g2012 -Wall "${defs[@]}" -s tb_css_phy_tx_top -o "results/sim/top_${rate}.vvp" "${RTL[@]}" tb/tb_css_phy_tx_top.sv
  iverilog -g2012 -Wall "${defs[@]}" -s tb_css_phy_protocol -o "results/sim/protocol_${rate}.vvp" "${RTL[@]}" tb/tb_css_phy_protocol.sv
  iverilog -g2012 -Wall "${defs[@]}" -s tb_css_phy_tx_multi -o "results/sim/multi_${rate}.vvp" "${RTL[@]}" tb/tb_css_phy_tx_multi.sv
  vvp "results/sim/protocol_${rate}.vvp"
  for len in 0 1 3 25 127; do
    vvp "results/sim/controller_${rate}.vvp" "+PLEN=$len" "+PAYLOAD=vectors/full_${rate}_len${len}_payload.hex" "+CHIPS=vectors/full_${rate}_len${len}_chips.txt"
    vvp "results/sim/top_${rate}.vvp" "+PLEN=$len" "+PAYLOAD=vectors/full_${rate}_len${len}_payload.hex" "+SAMPLES=vectors/full_${rate}_len${len}_samples.hex"
  done
  # Back-to-back packets: equal length + distinct contents between packets 1
  # and 2 detects payload/framing/modulator state leakage across packets.
  vvp "results/sim/multi_${rate}.vvp" \
    "+P1LEN=25" "+P1PAYLOAD=vectors/full_${rate}_len25_payload.hex" \
    "+P2LEN=25" "+P2PAYLOAD=vectors/full_${rate}_len25alt_payload.hex" \
    "+P3LEN=127" "+P3PAYLOAD=vectors/full_${rate}_len127alt_payload.hex" \
    "+P1SAMPLES=vectors/full_${rate}_len25_samples.hex" \
    "+P2SAMPLES=vectors/full_${rate}_len25alt_samples.hex" \
    "+P3SAMPLES=vectors/full_${rate}_len127alt_samples.hex"
done

echo "PASS: complete RTL regression"
