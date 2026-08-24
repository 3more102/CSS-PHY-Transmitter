# Project-independent Vivado implementation/timing flow.
# Run synthesis first with the same FPGA_PART / clock configuration.

set root [file normalize [file join [file dirname [info script]] ..]]
cd $root

if {![info exists ::env(FPGA_PART)] || $::env(FPGA_PART) eq ""} {
  error "FPGA_PART is required. No FPGA part was supplied; refusing to invent one."
}
set dcp results/vivado/css_phy_tx_post_synth.dcp
if {![file exists $dcp]} {
  error "$dcp not found; run scripts/vivado_synth.tcl first."
}

file mkdir reports/implementation
file mkdir results/vivado
open_checkpoint $dcp

# The checkpoint carries the part it was synthesized for.  Refuse to produce
# implementation evidence if the requested FPGA_PART does not match it, so a
# report can never be attributed to the wrong device.
set ckpt_part ""
if {![catch {set ckpt_part [get_property PART [current_design]]}]} {
  if {$ckpt_part ne "" && ![string equal -nocase $ckpt_part $::env(FPGA_PART)]} {
    error "FPGA_PART '$::env(FPGA_PART)' does not match checkpoint part '$ckpt_part'; re-run scripts/vivado_synth.tcl with the same part."
  }
} else {
  puts "WARNING: could not read PART from checkpoint; cross-check skipped."
}

if {[llength [get_clocks -quiet sys_clk]] != 1} {
  error "sys_clk constraint is missing in synthesis checkpoint; timing evidence would be invalid"
}

opt_design
place_design
phys_opt_design
route_design

report_utilization -file reports/implementation/impl_utilization.rpt
report_utilization -hierarchical -file reports/implementation/impl_utilization_hier.rpt
report_timing_summary -delay_type min_max -max_paths 50 -report_unconstrained \
  -file reports/implementation/impl_timing_summary.rpt
report_clock_utilization -file reports/implementation/impl_clock_utilization.rpt
report_drc -file reports/implementation/impl_drc.rpt
report_methodology -file reports/implementation/impl_methodology.rpt
report_route_status -file reports/implementation/impl_route_status.rpt
redirect -file reports/implementation/impl_check_timing.rpt {check_timing -verbose}

set fp [open reports/implementation/impl_clocks.txt w]
foreach c [get_clocks] {
  puts $fp "[get_property NAME $c] period_ns=[get_property PERIOD $c]"
}
close $fp

write_checkpoint -force results/vivado/css_phy_tx_post_route.dcp

set mf [open reports/implementation/impl_manifest.txt w]
puts $mf "part_requested=$::env(FPGA_PART)"
if {$ckpt_part ne ""} { puts $mf "part_from_checkpoint=$ckpt_part" }
puts $mf "vivado_version=[versionstring]"
puts $mf "generated_epoch=[clock seconds]"
close $mf

puts "IMPLEMENTATION COMPLETE. Bitstream intentionally not generated: board pin/IO constraints were not supplied."
