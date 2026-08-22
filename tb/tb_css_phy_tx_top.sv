`timescale 1ns/1ps
module tb_css_phy_tx_top;
`ifdef RATE250
  localparam integer RATE=1;
`else
  localparam integer RATE=0;
`endif
  logic clk=0,reset=0,start_Tx=0,payload_wr_en=0;
  logic [7:0] payloadLength;
  logic [6:0] payload_addr=0;
  logic [7:0] payload_din=0;
  logic done_Tx;
  logic signed [7:0] Tx_real,Tx_imag;
  integer plen,pfd,sfd,rc,k,tmp,count;
  logic [7:0] exp_r,exp_i;
  logic stream_started;
  reg [1023:0] payload_path,samples_path;
  always #5 clk=~clk;

  css_phy_tx_top #(.DATA_RATE(RATE),.CHIRP_INDEX(1)) dut(
    .clk(clk),.reset(reset),.start_Tx(start_Tx),.payloadLength(payloadLength),
    .payload_wr_en(payload_wr_en),.payload_addr(payload_addr),.payload_din(payload_din),
    .done_Tx(done_Tx),.Tx_real(Tx_real),.Tx_imag(Tx_imag));

  initial begin
    if(!$value$plusargs("PLEN=%d",plen)) $fatal(1,"PLEN plusarg required");
    if(!$value$plusargs("PAYLOAD=%s",payload_path)) $fatal(1,"PAYLOAD plusarg required");
    if(!$value$plusargs("SAMPLES=%s",samples_path)) $fatal(1,"SAMPLES plusarg required");
    payloadLength=plen[7:0];
    reset=1; repeat(2)@(posedge clk); reset=0;
    if(plen>0) begin
      pfd=$fopen(payload_path,"r"); if(!pfd)$fatal(1,"cannot open payload file");
      for(k=0;k<plen;k=k+1) begin
        rc=$fscanf(pfd,"%h\n",tmp); if(rc!=1)$fatal(1,"short payload file");
        @(negedge clk); payload_addr=k[6:0]; payload_din=tmp[7:0]; payload_wr_en=1;
        @(posedge clk); #1; payload_wr_en=0;
      end
      $fclose(pfd);
    end
    sfd=$fopen(samples_path,"r"); if(!sfd)$fatal(1,"cannot open sample vector");
    @(negedge clk); start_Tx=1; @(negedge clk); start_Tx=0;
    count=0; stream_started=0;
    forever begin
      @(posedge clk); #1;
      if(dut.sample_valid_int) begin
        stream_started=1;
        rc=$fscanf(sfd,"%h %h\n",exp_r,exp_i);
        if(rc!=2)$fatal(1,"unexpected extra sample at %0d",count);
        if(Tx_real!==exp_r || Tx_imag!==exp_i)
          $fatal(1,"top mismatch rate=%0d plen=%0d sample=%0d exp=%h,%h got=%h,%h",
                 RATE,plen,count,exp_r,exp_i,Tx_real,Tx_imag);
        count=count+1;
      end else if(stream_started && !done_Tx) begin
        $fatal(1,"sample stream bubble after sample %0d",count);
      end
      if(done_Tx) begin
        rc=$fscanf(sfd,"%h %h\n",exp_r,exp_i); if(rc==2)$fatal(1,"done_Tx asserted before vector EOF");
        $fclose(sfd); $display("PASS tb_css_phy_tx_top rate=%0d plen=%0d samples=%0d",RATE,plen,count); $finish;
      end
    end
  end
  initial begin #20000000; $fatal(1,"timeout"); end
endmodule
