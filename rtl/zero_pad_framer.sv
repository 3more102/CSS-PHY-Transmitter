module zero_pad_framer (
  input  logic       rate,
  input  logic [7:0] payload_length,
  output logic [5:0] pad_bits,
  output logic [10:0] total_bits
);
  integer n;
  integer base_bits;
  integer rem_bits;
  integer pad_i;
  always_comb begin
    n = rate ? 24 : 6;
    base_bits = 12 + (payload_length * 8);
    rem_bits = base_bits % n;
    // Exact supplied MATLAB behavior: N - mod(...,N). Therefore a complete
    // N-bit zero block is appended when rem_bits==0.
    pad_i = n - rem_bits;
    pad_bits = pad_i[5:0];
    total_bits = base_bits + pad_i;
  end
endmodule
