module preamble_sfd_rom (
  input  logic       rate,
  input  logic [6:0] index,
  output logic       chip,
  output logic       valid
);
  localparam logic [15:0] SFD_1M   = 16'b0111010010011100;
  localparam logic [15:0] SFD_250K = 16'b0111101000100011;
  integer pre_len;
  integer sfd_idx;
  always_comb begin
    pre_len = rate ? 80 : 32;
    chip = 1'b0;
    valid = 1'b0;
    if (index < pre_len) begin
      chip = 1'b1; // +1 preamble chip
      valid = 1'b1;
    end else if (index < pre_len + 16) begin
      sfd_idx = index - pre_len;
      chip = rate ? SFD_250K[15-sfd_idx] : SFD_1M[15-sfd_idx];
      valid = 1'b1;
    end
  end
endmodule
