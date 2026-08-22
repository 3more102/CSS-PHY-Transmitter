module chirp_rom #(
  parameter string M1_REAL = "rtl/rom/chirp_m1_real.mem",
  parameter string M1_IMAG = "rtl/rom/chirp_m1_imag.mem",
  parameter string M2_REAL = "rtl/rom/chirp_m2_real.mem",
  parameter string M2_IMAG = "rtl/rom/chirp_m2_imag.mem",
  parameter string M3_REAL = "rtl/rom/chirp_m3_real.mem",
  parameter string M3_IMAG = "rtl/rom/chirp_m3_imag.mem",
  parameter string M4_REAL = "rtl/rom/chirp_m4_real.mem",
  parameter string M4_IMAG = "rtl/rom/chirp_m4_imag.mem"
) (
  input  logic [2:0] chirp_index,
  input  logic [7:0] addr,
  output logic signed [5:0] chirp_real,
  output logic signed [5:0] chirp_imag
);
  logic signed [5:0] m1r [0:151], m1i [0:151];
  logic signed [5:0] m2r [0:151], m2i [0:151];
  logic signed [5:0] m3r [0:151], m3i [0:151];
  logic signed [5:0] m4r [0:151], m4i [0:151];

  initial begin
    $readmemb(M1_REAL, m1r); $readmemb(M1_IMAG, m1i);
    $readmemb(M2_REAL, m2r); $readmemb(M2_IMAG, m2i);
    $readmemb(M3_REAL, m3r); $readmemb(M3_IMAG, m3i);
    $readmemb(M4_REAL, m4r); $readmemb(M4_IMAG, m4i);
  end

  always_comb begin
    chirp_real = 6'sd0;
    chirp_imag = 6'sd0;
    if (addr < 8'd152) begin
      unique case (chirp_index)
        3'd1: begin chirp_real = m1r[addr]; chirp_imag = m1i[addr]; end
        3'd2: begin chirp_real = m2r[addr]; chirp_imag = m2i[addr]; end
        3'd3: begin chirp_real = m3r[addr]; chirp_imag = m3i[addr]; end
        3'd4: begin chirp_real = m4r[addr]; chirp_imag = m4i[addr]; end
        default: begin chirp_real = 6'sd0; chirp_imag = 6'sd0; end
      endcase
    end
  end
endmodule
