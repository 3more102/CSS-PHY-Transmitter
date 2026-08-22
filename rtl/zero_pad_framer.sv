module zero_pad_framer (
  input  logic       rate,
  input  logic [7:0] payload_length,
  output logic [5:0] pad_bits,
  output logic [10:0] total_bits
);
  logic [5:0] n;
  logic [10:0] base_bits;
  logic [10:0] rem_bits;

  always_comb begin
    n = rate ? 6'd24 : 6'd6;
    base_bits = 11'd12 + ({3'd0, payload_length} << 3);
    rem_bits = base_bits % n;
    // Exact supplied MATLAB behavior: N - mod(...,N). Therefore a complete
    // N-bit zero block is appended when the remainder is zero.
    pad_bits = n - rem_bits[5:0];
    total_bits = base_bits + {5'd0, pad_bits};
  end
endmodule
