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
  integer k;

  always_comb begin
    // Explicit sized casts preserve the supplied fixed-width wrap semantics
    // while avoiding an implicit truncation of wider intermediate products.
    out_real = 3'(
      $signed(in_real) * $signed(fb_real[phase])
      - $signed(in_imag) * $signed(fb_imag[phase])
    );
    out_imag = 3'(
      $signed(in_real) * $signed(fb_imag[phase])
      + $signed(in_imag) * $signed(fb_real[phase])
    );
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
