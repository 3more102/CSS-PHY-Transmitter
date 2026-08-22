`timescale 1ns/1ps
module tb_payload_ram;
  logic clk=0, wr_en=0;
  logic [6:0] wr_addr, rd_addr;
  logic [7:0] wr_data, rd_data;
  always #5 clk=~clk;
  payload_ram dut(.clk(clk),.wr_en(wr_en),.wr_addr(wr_addr),.wr_data(wr_data),.rd_addr(rd_addr),.rd_data(rd_data));

  task automatic write_check(input integer addr, input integer data);
    begin
      @(negedge clk); wr_addr=addr[6:0]; wr_data=data[7:0]; wr_en=1;
      @(posedge clk); #1; wr_en=0; rd_addr=addr[6:0]; #1;
      if(rd_data!==data[7:0]) $fatal(1,"payload RAM addr=%0d expected=%h got=%h",addr,data[7:0],rd_data);
    end
  endtask

  initial begin
    wr_addr=0; wr_data=0; rd_addr=0;
    write_check(0,8'h01); write_check(1,8'h80); write_check(126,8'h96); write_check(127,8'hA5);
    $display("PASS tb_payload_ram"); $finish;
  end
  initial begin #1000; $fatal(1,"timeout"); end
endmodule
