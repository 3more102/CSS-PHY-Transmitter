`timescale 1ns/1ps
module tb_symbol_mapper_250k;
  logic [5:0] symbol;
  logic [31:0] codeword;
  integer fd, rc, sym_i, count;
  logic [31:0] expected;
  symbol_mapper_250k dut(.symbol(symbol), .codeword(codeword));
  initial begin
    fd=$fopen("vectors/symbol_mapper_250k.txt","r");
    if (!fd) $fatal(1,"cannot open vector file");
    count=0;
    while (!$feof(fd)) begin
      rc=$fscanf(fd,"%d %b\n",sym_i,expected);
      if (rc==2) begin
        symbol=sym_i[5:0]; #1;
        if (codeword !== expected) $fatal(1,"mapper250 symbol=%0d expected=%b actual=%b",sym_i,expected,codeword);
        count=count+1;
      end
    end
    $fclose(fd);
    if (count!=64) $fatal(1,"expected 64 vectors, got %0d",count);
    $display("PASS tb_symbol_mapper_250k"); $finish;
  end
endmodule
