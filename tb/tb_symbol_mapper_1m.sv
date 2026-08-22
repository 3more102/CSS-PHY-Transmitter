`timescale 1ns/1ps
module tb_symbol_mapper_1m;
  logic [2:0] symbol;
  logic [3:0] codeword;
  logic [3:0] expected [0:7];
  integer k;
  symbol_mapper_1m dut(.symbol(symbol), .codeword(codeword));
  initial begin
    expected[0]=4'b1111; expected[1]=4'b1010; expected[2]=4'b1100; expected[3]=4'b1001;
    expected[4]=4'b0000; expected[5]=4'b0101; expected[6]=4'b0011; expected[7]=4'b0110;
    for (k=0;k<8;k=k+1) begin
      symbol=k[2:0]; #1;
      if (codeword !== expected[k]) $fatal(1,"mapper1m symbol=%0d expected=%b actual=%b",k,expected[k],codeword);
    end
    $display("PASS tb_symbol_mapper_1m"); $finish;
  end
endmodule
