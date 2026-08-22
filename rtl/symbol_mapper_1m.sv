module symbol_mapper_1m (
  input  logic [2:0] symbol,
  output logic [3:0] codeword
);
  // Packed vector is written c0..c3 from MSB to LSB. Transmit c0 first.
  always_comb begin
    unique case (symbol)
      3'd0: codeword = 4'b1111;
      3'd1: codeword = 4'b1010;
      3'd2: codeword = 4'b1100;
      3'd3: codeword = 4'b1001;
      3'd4: codeword = 4'b0000;
      3'd5: codeword = 4'b0101;
      3'd6: codeword = 4'b0011;
      3'd7: codeword = 4'b0110;
      default: codeword = 4'b0000;
    endcase
  end
endmodule
