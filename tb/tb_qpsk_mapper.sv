`timescale 1ns/1ps
module tb_qpsk_mapper;
  logic chip_i, chip_q;
  logic signed [2:0] r,i;
  qpsk_mapper dut(.chip_i(chip_i),.chip_q(chip_q),.qpsk_real(r),.qpsk_imag(i));
  task automatic check(input logic ci,input logic cq,input integer er,input integer ei);
    begin chip_i=ci; chip_q=cq; #1;
      if ($signed(r)!==er || $signed(i)!==ei) $fatal(1,"QPSK %b%b exp=(%0d,%0d) got=(%0d,%0d)",ci,cq,er,ei,$signed(r),$signed(i));
    end
  endtask
  initial begin
    check(1,1, 1,0); check(1,0, 0,-1); check(0,1, 0,1); check(0,0,-1,0);
    $display("PASS tb_qpsk_mapper"); $finish;
  end
endmodule
