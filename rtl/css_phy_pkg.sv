package css_phy_pkg;
  localparam int RATE_1M   = 0;
  localparam int RATE_250K = 1;
  localparam int PHR_BITS  = 12;
  localparam int SFD_BITS  = 16;
  localparam logic [8:0] TSUB_SAMPLES = 9'd38;
  localparam logic [8:0] ACTIVE_CHIRP_SAMPLES = 9'd152;
  localparam logic [7:0] MAX_PAYLOAD_BYTES = 8'd127;

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
