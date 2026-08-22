module symbol_mapper_250k #(
  parameter string ROM_FILE = "rtl/rom/codeword_250k.mem"
) (
  input  logic [5:0]  symbol,
  output logic [31:0] codeword
);
  logic [31:0] rom [0:63];
  initial $readmemb(ROM_FILE, rom);
  always_comb codeword = rom[symbol];
endmodule
