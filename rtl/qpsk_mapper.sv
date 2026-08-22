module qpsk_mapper (
  input  logic chip_i, // 1 => +1, 0 => -1
  input  logic chip_q,
  output logic signed [2:0] qpsk_real,
  output logic signed [2:0] qpsk_imag
);
  always_comb begin
    qpsk_real = 3'sd0;
    qpsk_imag = 3'sd0;
    unique case ({chip_i, chip_q})
      2'b11: begin qpsk_real =  3'sd1; qpsk_imag =  3'sd0; end
      2'b10: begin qpsk_real =  3'sd0; qpsk_imag = -3'sd1; end
      2'b01: begin qpsk_real =  3'sd0; qpsk_imag =  3'sd1; end
      2'b00: begin qpsk_real = -3'sd1; qpsk_imag =  3'sd0; end
      default: begin qpsk_real = 3'sd0; qpsk_imag = 3'sd0; end
    endcase
  end
endmodule
