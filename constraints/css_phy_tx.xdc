# Timing-only constraints for the board-independent CSS PHY transmitter.
# No LOC / IOSTANDARD constraints are invented because no board was supplied.
# Overrides are accepted through the environment so the same source can be used
# for a real target without editing this file:
#   CLOCK_PORT=clk
#   CLOCK_PERIOD_NS=31.250

set clock_port "clk"
if {[info exists ::env(CLOCK_PORT)] && $::env(CLOCK_PORT) ne ""} {
  set clock_port $::env(CLOCK_PORT)
}

set clock_period_ns 31.250
if {[info exists ::env(CLOCK_PERIOD_NS)] && $::env(CLOCK_PERIOD_NS) ne ""} {
  set clock_period_ns $::env(CLOCK_PERIOD_NS)
}

set clock_ports [get_ports -quiet $clock_port]
if {[llength $clock_ports] != 1} {
  error "CLOCK_PORT '$clock_port' did not resolve to exactly one top-level port"
}
create_clock -name sys_clk -period $clock_period_ns $clock_ports
