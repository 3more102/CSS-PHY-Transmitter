module phr_generator (
  input  logic [7:0]  payload_length,
  output logic [11:0] phr_bits
);
  integer i;
  always_comb begin
    phr_bits = '0;
    // phr_bits[0] is the first transmitted PHR bit. MATLAB sends payload
    // length bit 0 first through bit 6, followed by five zero bits.
    for (i = 0; i < css_phy_pkg::PHR_BITS - 5; i = i + 1)
      phr_bits[i] = payload_length[i];
  end
endmodule
