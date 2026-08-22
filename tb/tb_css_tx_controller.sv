`timescale 1ns/1ps
module tb_css_tx_controller;
`ifdef RATE250
  localparam logic RATE=1'b1;
`else
  localparam logic RATE=1'b0;
`endif
  logic clk=0,reset=0,start=0;
  logic [7:0] payload_length;
  logic [6:0] payload_rd_addr;
  logic [7:0] payload_rd_data;
  logic chip_valid,chip_ready=1,chip_i,chip_q,source_done,busy;
  logic [7:0] payload_mem[0:127];
  integer plen,pfd,cfd,rc,k,tmp,exp_i,exp_q,count;
  reg [1023:0] payload_path,chips_path;
  always #5 clk=~clk;
  always_comb payload_rd_data=payload_mem[payload_rd_addr];
  css_tx_controller dut(.clk(clk),.reset(reset),.start(start),.rate(RATE),.payload_length(payload_length),
    .payload_rd_addr(payload_rd_addr),.payload_rd_data(payload_rd_data),.chip_valid(chip_valid),.chip_ready(chip_ready),
    .chip_i(chip_i),.chip_q(chip_q),.source_done(source_done),.busy(busy));
  initial begin
    if(!$value$plusargs("PLEN=%d",plen)) $fatal(1,"PLEN plusarg required");
    if(!$value$plusargs("PAYLOAD=%s",payload_path)) $fatal(1,"PAYLOAD plusarg required");
    if(!$value$plusargs("CHIPS=%s",chips_path)) $fatal(1,"CHIPS plusarg required");
    for(k=0;k<128;k=k+1) payload_mem[k]=0;
    if(plen>0) begin
      pfd=$fopen(payload_path,"r"); if(!pfd)$fatal(1,"cannot open payload");
      for(k=0;k<plen;k=k+1) begin rc=$fscanf(pfd,"%h\n",tmp); if(rc!=1)$fatal(1,"short payload"); payload_mem[k]=tmp[7:0]; end
      $fclose(pfd);
    end
    cfd=$fopen(chips_path,"r"); if(!cfd)$fatal(1,"cannot open chip vector");
    payload_length=plen[7:0]; reset=1; repeat(2)@(posedge clk); reset=0;
    @(negedge clk); start=1; @(negedge clk); start=0; count=0;
    forever begin
      @(posedge clk);
      // Sample the chip in the handshake cycle before DUT nonblocking state/index
      // updates take effect. A #1 delay here would observe the next chip and
      // create a one-chip scoreboard skew at preamble/SFD boundaries.
      if(chip_valid && chip_ready) begin
        rc=$fscanf(cfd,"%d %d\n",exp_i,exp_q); if(rc!=2)$fatal(1,"unexpected extra chip %0d",count);
        if(chip_i!==(exp_i!=0) || chip_q!==(exp_q!=0))
          $fatal(1,"controller mismatch rate=%0d plen=%0d chip=%0d exp=(%0d,%0d) got=(%0d,%0d)",
                 RATE,plen,count,exp_i,exp_q,chip_i,chip_q);
        count=count+1;
      end
      #1;
      if(source_done) begin
        rc=$fscanf(cfd,"%d %d\n",exp_i,exp_q); if(rc==2)$fatal(1,"controller ended early");
        $fclose(cfd); $display("PASS tb_css_tx_controller rate=%0d plen=%0d chips=%0d",RATE,plen,count); $finish;
      end
    end
  end
  initial begin #5000000; $fatal(1,"timeout"); end
endmodule
