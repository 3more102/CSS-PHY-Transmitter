module dqpsk_encoder (
  input  logic clk,
  input  logic reset,
  input  logic init_packet,
  input  logic in_valid,
  input  logic accept,
  input  logic signed [2:0] in_real,
  input  logic signed [2:0] in_imag,
  output logic out_valid,
  output logic signed [2:0] out_real,
  output logic signed [2:0] out_imag
);
  logic signed [2:0] fb_real [0:3];
  logic signed [2:0] fb_imag [0:3];
  logic [1:0] phase;
  logic signed [6:0] calc_real;
  logic signed [6:0] calc_imag;
  integer k;

  always_comb begin
    calc_real = $signed(in_real) * $signed(fb_real[phase])
              - $signed(in_imag) * $signed(fb_imag[phase]);
    calc_imag = $signed(in_real) * $signed(fb_imag[phase])
              + $signed(in_imag) * $signed(fb_real[phase]);
    out_real = calc_real[2:0];
    out_imag = calc_imag[2:0];
    out_valid = in_valid && accept;
  end

  always_ff @(posedge clk) begin
    if (reset || init_packet) begin
      phase <= 2'd0;
      for (k = 0; k < 4; k = k + 1) begin
        // Supplied fixed-point MATLAB removes normalization and initializes
        // each stage to 1+j rather than 1/sqrt(2)+j/sqrt(2).
        fb_real[k] <= 3'sd1;
        fb_imag[k] <= 3'sd1;
      end
    end else if (out_valid) begin
      fb_real[phase] <= out_real;
      fb_imag[phase] <= out_imag;
      phase <= phase + 2'd1;
    end
  end
endmodule
