`timescale 1ns/1ps
module tb_phr_generator;
  logic [7:0] payload_length;
  logic [11:0] phr_bits;
  logic [11:0] expected;
  phr_generator dut(.payload_length(payload_length), .phr_bits(phr_bits));

  task automatic check(input integer plen);
    begin
      payload_length = plen[7:0];
      expected = {5'b0, plen[6:0]};
      #1;
      if (phr_bits !== expected)
        $fatal(1,"PHR plen=%0d expected=%b got=%b", plen, expected, phr_bits);
    end
  endtask

  initial begin
    check(0); check(1); check(25); check(96); check(127);
    $display("PASS tb_phr_generator");
    $finish;
  end
endmodule
