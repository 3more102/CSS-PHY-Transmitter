`timescale 1ns/1ps
module tb_iq_demux;
  logic pair_valid, first_bit, second_bit;
  logic i_valid, q_valid, i_bit, q_bit;
  iq_demux dut(.pair_valid(pair_valid), .first_bit(first_bit), .second_bit(second_bit),
               .i_valid(i_valid), .q_valid(q_valid), .i_bit(i_bit), .q_bit(q_bit));

  initial begin
    pair_valid=0; first_bit=1; second_bit=0; #1;
    if(i_valid || q_valid) $fatal(1,"invalid pair propagated valid");
    pair_valid=1; first_bit=1; second_bit=0; #1;
    if(!i_valid || !q_valid || i_bit!==1'b1 || q_bit!==1'b0)
      $fatal(1,"first/second pair did not route to I/Q");
    first_bit=0; second_bit=1; #1;
    if(i_bit!==1'b0 || q_bit!==1'b1)
      $fatal(1,"asymmetric 0/1 pair did not route to I/Q");
    $display("PASS tb_iq_demux");
    $finish;
  end
endmodule
