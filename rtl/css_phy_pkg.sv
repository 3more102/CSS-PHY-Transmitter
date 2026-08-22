package css_phy_pkg;
  localparam int RATE_1M   = 0;
  localparam int RATE_250K = 1;
  localparam int PHR_BITS  = 12;
  localparam int SFD_BITS  = 16;
  localparam int TSUB_SAMPLES = 38;
  localparam int ACTIVE_CHIRP_SAMPLES = 152;
  localparam int MAX_PAYLOAD_BYTES = 127;

  function automatic int pad_modulus(input logic rate);
    pad_modulus = rate ? 24 : 6;
  endfunction

  function automatic int bits_per_symbol(input logic rate);
    bits_per_symbol = rate ? 6 : 3;
  endfunction

  function automatic int preamble_length(input logic rate);
    preamble_length = rate ? 80 : 32;
  endfunction
endpackage
