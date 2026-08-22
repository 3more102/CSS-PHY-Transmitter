module payload_ram (
  input  logic       clk,
  input  logic       wr_en,
  input  logic [6:0] wr_addr,
  input  logic [7:0] wr_data,
  input  logic [6:0] rd_addr,
  output logic [7:0] rd_data
);
  logic [7:0] mem [0:127];

  always_ff @(posedge clk) begin
    if (wr_en)
      mem[wr_addr] <= wr_data;
  end

  // Asynchronous read keeps the pairwise bit collector simple. Vivado may
  // infer distributed RAM. A synchronous-BRAM wrapper can be substituted
  // without changing the PHY algorithms.
  always_comb rd_data = mem[rd_addr];
endmodule
