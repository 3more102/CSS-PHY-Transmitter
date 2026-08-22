module preamble_sfd_rom (
  input  logic       rate,
  input  logic [6:0] index,
  output logic       chip,
  output logic       valid
);
  localparam logic [css_phy_pkg::SFD_BITS-1:0] SFD_1M   = 16'b0111010010011100;
  localparam logic [css_phy_pkg::SFD_BITS-1:0] SFD_250K = 16'b0111101000100011;

  // Both preamble lengths are multiples of 16, so index[3:0] is the SFD-local
  // offset in the 16-chip SFD windows. All comparisons and indices are sized.
  always_comb begin
    chip = 1'b0;
    valid = 1'b0;
    if (!rate) begin
      if (index < 7'd32) begin
        chip = 1'b1;
        valid = 1'b1;
      end else if (index < 7'd48) begin
        chip = SFD_1M[4'd15 - index[3:0]];
        valid = 1'b1;
      end
    end else begin
      if (index < 7'd80) begin
        chip = 1'b1;
        valid = 1'b1;
      end else if (index < 7'd96) begin
        chip = SFD_250K[4'd15 - index[3:0]];
        valid = 1'b1;
      end
    end
  end
endmodule
