#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if ! command -v verilator >/dev/null 2>&1; then
  echo "BLOCKED: Verilator is not installed." >&2
  exit 2
fi

# Keep lint strict: any Verilator warning is a verification failure. Intentional
# fixed-width behavior is expressed explicitly in the RTL instead of weakening
# the global warning-fatal policy.
verilator --lint-only --timing -Wall \
  rtl/css_phy_pkg.sv rtl/payload_ram.sv rtl/phr_generator.sv rtl/zero_pad_framer.sv rtl/iq_demux.sv \
  rtl/symbol_mapper_1m.sv rtl/symbol_mapper_250k.sv rtl/bit_interleaver.sv rtl/preamble_sfd_rom.sv \
  rtl/qpsk_mapper.sv rtl/dqpsk_encoder.sv rtl/chirp_rom.sv rtl/csk_modulator.sv rtl/css_tx_controller.sv rtl/css_phy_tx_top.sv \
  --top-module css_phy_tx_top
