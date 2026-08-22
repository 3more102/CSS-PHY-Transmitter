`timescale 1ns/1ps
module tb_interleaver;
  logic [63:0] in_bits, out_bits, expected;
  integer fd, rc, out_idx, in_idx, count;
  bit_interleaver dut(.in_bits(in_bits), .out_bits(out_bits));
  initial begin
    fd=$fopen("vectors/interleaver_250k_indices.txt","r");
    if (!fd) $fatal(1,"cannot open interleaver vector");
    count=0;
    while (!$feof(fd)) begin
      rc=$fscanf(fd,"%d %d\n",out_idx,in_idx);
      if (rc==2) begin
        in_bits=64'b0; expected=64'b0;
        in_bits[63-in_idx]=1'b1;
        expected[63-out_idx]=1'b1;
        #1;
        if (out_bits !== expected) $fatal(1,"interleaver output=%0d input=%0d mismatch",out_idx,in_idx);
        count=count+1;
      end
    end
    $fclose(fd);
    if (count!=64) $fatal(1,"expected 64 permutation entries, got %0d",count);
    $display("PASS tb_interleaver"); $finish;
  end
endmodule
