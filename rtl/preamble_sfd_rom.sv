module preamble_sfd_rom (
  input  logic       rate,
  input  logic [6:0] index,
  output logic       chip,
  output logic       valid
);
  localparam logic [15:0] SFD_1M   = 16'b0111010010011100;
  localparam logic [15:0] SFD_250K = 16'b0111101000100011;

  // Keep all comparisons explicitly sized.  The two rate branches are
  // intentionally written out because their preamble lengths are constants;
  // this avoids inferred temporary state and makes the SFD index bounds clear.
  always_comb begin
    chip = 1'b0;
    valid = 1'b0;
    if (!rate) begin
      if (index < 7'd32) begin
        chip = 1'b1;
        valid = 1'b1;
      end else if (index < 7'd48) begin
        chip = SFD_1M[7'd47 - index];
        valid = 1'b1;
      end
    end else begin
      if (index < 7'd80) begin
        chip = 1'b1;
        valid = 1'b1;
      end else if (index < 7'd96) begin
        chip = SFD_250K[7'd95 - index];
        valid = 1'b1;
      end
    end
  end
endmodule
