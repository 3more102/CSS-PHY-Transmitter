`timescale 1ns/1ps
module tb_zero_pad_framer;
  logic rate;
  logic [7:0] payload_length;
  logic [5:0] pad_bits;
  logic [10:0] total_bits;
  zero_pad_framer dut(.rate(rate), .payload_length(payload_length), .pad_bits(pad_bits), .total_bits(total_bits));

  task automatic check(input bit r, input integer plen, input integer exp_pad, input integer exp_total);
    begin
      rate = r; payload_length = plen[7:0]; #1;
      if (pad_bits !== exp_pad[5:0] || total_bits !== exp_total[10:0])
        $fatal(1,"padding rate=%0d plen=%0d exp=(%0d,%0d) got=(%0d,%0d)",
               r, plen, exp_pad, exp_total, pad_bits, total_bits);
    end
  endtask

  initial begin
    check(0,   0,  6,   18);
    check(0,   1,  4,   24);
    check(0,   3,  6,   42);
    check(0, 127,  4, 1032);
    check(1,   0, 12,   24);
    check(1,   1,  4,   24);
    check(1,   3, 12,   48);
    check(1, 127,  4, 1032);
    $display("PASS tb_zero_pad_framer");
    $finish;
  end
endmodule
