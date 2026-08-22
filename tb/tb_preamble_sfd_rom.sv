`timescale 1ns/1ps
module tb_preamble_sfd_rom;
  logic rate;
  logic [6:0] index;
  logic chip, valid;
  integer k;
  logic [15:0] sfd;
  integer pre_len;
  preamble_sfd_rom dut(.rate(rate), .index(index), .chip(chip), .valid(valid));

  task automatic check_rate(input bit r);
    begin
      rate = r;
      pre_len = r ? 80 : 32;
      sfd = r ? 16'b0111101000100011 : 16'b0111010010011100;
      for(k=0;k<pre_len;k=k+1) begin
        index=k[6:0]; #1;
        if(!valid || chip!==1'b1) $fatal(1,"preamble rate=%0d index=%0d mismatch",r,k);
      end
      for(k=0;k<16;k=k+1) begin
        index=(pre_len+k); #1;
        if(!valid || chip!==sfd[15-k]) $fatal(1,"SFD rate=%0d bit=%0d mismatch",r,k);
      end
      index=(pre_len+16); #1;
      if(valid) $fatal(1,"sync ROM remained valid past end rate=%0d",r);
    end
  endtask

  initial begin
    check_rate(0); check_rate(1);
    $display("PASS tb_preamble_sfd_rom");
    $finish;
  end
endmodule
