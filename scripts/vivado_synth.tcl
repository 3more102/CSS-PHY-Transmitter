# Project-independent Vivado synthesis flow for CSS PHY Transmitter.
# Required:
#   FPGA_PART=<exact Xilinx part>
# Optional:
#   TOP=css_phy_tx_top
#   CLOCK_PORT=clk
#   CLOCK_PERIOD_NS=31.250
#   DATA_RATE=0|1
#   CHIRP_INDEX=1..4
#   SAMPLE_DIV=<integer >= 1>

set root [file normalize [file join [file dirname [info script]] ..]]
cd $root

if {![info exists ::env(FPGA_PART)] || $::env(FPGA_PART) eq ""} {
  error "FPGA_PART is required. No FPGA part was supplied; refusing to invent one."
}
set part $::env(FPGA_PART)
set top "css_phy_tx_top"
if {[info exists ::env(TOP)] && $::env(TOP) ne ""} { set top $::env(TOP) }
set rate 0
if {[info exists ::env(DATA_RATE)] && $::env(DATA_RATE) ne ""} { set rate $::env(DATA_RATE) }
set chirp 1
if {[info exists ::env(CHIRP_INDEX)] && $::env(CHIRP_INDEX) ne ""} { set chirp $::env(CHIRP_INDEX) }
set sdiv 1
if {[info exists ::env(SAMPLE_DIV)] && $::env(SAMPLE_DIV) ne ""} { set sdiv $::env(SAMPLE_DIV) }

file mkdir reports/synthesis
file mkdir results/vivado

set rtl_files [list \
  rtl/css_phy_pkg.sv rtl/payload_ram.sv rtl/phr_generator.sv rtl/zero_pad_framer.sv rtl/iq_demux.sv \
  rtl/symbol_mapper_1m.sv rtl/symbol_mapper_250k.sv rtl/bit_interleaver.sv rtl/preamble_sfd_rom.sv \
  rtl/qpsk_mapper.sv rtl/dqpsk_encoder.sv rtl/chirp_rom.sv rtl/csk_modulator.sv \
  rtl/css_tx_controller.sv rtl/css_phy_tx_top.sv]

read_verilog -sv $rtl_files
read_xdc constraints/css_phy_tx.xdc

synth_design -top $top -part $part \
  -generic DATA_RATE=$rate -generic CHIRP_INDEX=$chirp -generic SAMPLE_DIV=$sdiv

if {[llength [get_clocks -quiet sys_clk]] != 1} {
  error "sys_clk constraint is missing after synthesis; refusing to report timing as valid"
}

report_utilization -file reports/synthesis/synth_utilization.rpt
report_utilization -hierarchical -file reports/synthesis/synth_utilization_hier.rpt
report_timing_summary -delay_type max -max_paths 20 -report_unconstrained \
  -file reports/synthesis/synth_timing_summary.rpt
report_clock_utilization -file reports/synthesis/synth_clock_utilization.rpt
report_methodology -file reports/synthesis/synth_methodology.rpt
redirect -file reports/synthesis/synth_check_timing.rpt {check_timing -verbose}

set fp [open reports/synthesis/synth_clocks.txt w]
foreach c [get_clocks] {
  puts $fp "[get_property NAME $c] period_ns=[get_property PERIOD $c]"
}
close $fp

write_checkpoint -force results/vivado/css_phy_tx_post_synth.dcp
puts "SYNTHESIS COMPLETE: part=$part top=$top DATA_RATE=$rate CHIRP_INDEX=$chirp SAMPLE_DIV=$sdiv"
