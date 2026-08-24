`timescale 1ns/1ps
module tb_css_phy_tx_reset_sweep;
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
  integer pfd,sfd,rc,k,tmp,count,cycles,dones;
  logic [7:0] exp_r,exp_i;
  reg [1023:0] payload_path,samples_path;
  integer plen;
  integer OFFSETS[0:5];
  integer attempt;
  logic aborted;
  always #5 clk=~clk;

  css_phy_tx_top #(.DATA_RATE(RATE),.CHIRP_INDEX(1)) dut(
    .clk(clk),.reset(reset),.start_Tx(start_Tx),.payloadLength(payloadLength),
    .payload_wr_en(payload_wr_en),.payload_addr(payload_addr),.payload_din(payload_din),
    .done_Tx(done_Tx),.Tx_real(Tx_real),.Tx_imag(Tx_imag));

  task automatic do_reset;
    begin
      @(negedge clk); reset=1;
      repeat(2) @(posedge clk);
      @(negedge clk); reset=0;
    end
  endtask

  task automatic load_payload;
    begin
      payloadLength=plen[7:0]; payload_wr_en=0;
      if(plen>0) begin
        pfd=$fopen(payload_path,"r"); if(!pfd)$fatal(1,"cannot open payload file");
        for(k=0;k<plen;k=k+1) begin
          rc=$fscanf(pfd,"%h\n",tmp); if(rc!=1)$fatal(1,"short payload file");
          @(negedge clk); payload_addr=k[6:0]; payload_din=tmp[7:0]; payload_wr_en=1;
          @(posedge clk); #1; payload_wr_en=0;
        end
        $fclose(pfd);
      end
    end
  endtask

  task automatic verify_idle_after_reset(input integer o);
    begin
      repeat(2) @(posedge clk); #1;
      if(dut.tx_active || dut.controller_busy || dut.csk_busy || done_Tx)
        $fatal(1,"rate=%0d reset@%0d did not return transmitter to idle",RATE,o);
      if(Tx_real!==8'sd0 || Tx_imag!==8'sd0)
        $fatal(1,"rate=%0d reset@%0d did not clear output samples",RATE,o);
      if(dut.sample_valid_int)
        $fatal(1,"rate=%0d reset@%0d left sample_valid asserted",RATE,o);
    end
  endtask

  task automatic full_packet_check(input integer o,input integer expect_done);
    begin
      sfd=$fopen(samples_path,"r"); if(!sfd)$fatal(1,"cannot open sample vector");
      load_payload();
      @(negedge clk); start_Tx=1; @(negedge clk); start_Tx=0;
      count=0; cycles=0; dones=0; aborted=0;
      forever begin
        @(posedge clk); #1;
        if(dut.sample_valid_int) begin
          rc=$fscanf(sfd,"%h %h\n",exp_r,exp_i);
          if(rc!=2)$fatal(1,"rate=%0d reset@%0d extra sample %0d",RATE,o,count);
          if(Tx_real!==exp_r || Tx_imag!==exp_i)
            $fatal(1,"rate=%0d reset@%0d mismatch sample=%0d exp=%h,%h got=%h,%h",
                   RATE,o,count,exp_r,exp_i,Tx_real,Tx_imag);
          count=count+1;
        end
        if(done_Tx) begin
          dones=dones+1;
          if(dones>1)$fatal(1,"rate=%0d reset@%0d done pulsed twice",RATE,o);
          rc=$fscanf(sfd,"%h %h\n",exp_r,exp_i);
          if(rc==2)$fatal(1,"rate=%0d reset@%0d done before vector EOF",RATE,o);
          $fclose(sfd);
          return;
        end
        if(expect_done==0 && !aborted) begin
          cycles=cycles+1;
          if(cycles==o) begin
            aborted=1;
            @(negedge clk); reset=1;
            repeat(2) @(posedge clk);
            @(negedge clk); reset=0;
            $fclose(sfd);
            verify_idle_after_reset(o);
            return;
          end
        end
      end
    end
  endtask

  initial begin
    if(!$value$plusargs("PLEN=%d",plen))$fatal(1,"PLEN required");
    if(!$value$plusargs("PAYLOAD=%s",payload_path))$fatal(1,"PAYLOAD required");
    if(!$value$plusargs("SAMPLES=%s",samples_path))$fatal(1,"SAMPLES required");
    OFFSETS[0]=5;   // mid-preamble
    OFFSETS[1]=33;  // preamble tail / near SFD start
    OFFSETS[2]=47;  // SFD region boundary
    OFFSETS[3]=63;  // PHR transmission window
    OFFSETS[4]=97;  // early payload symbols
    OFFSETS[5]=211; // deep into payload

    do_reset();
    for(attempt=0;attempt<6;attempt=attempt+1) begin
      full_packet_check(OFFSETS[attempt],0);
      full_packet_check(OFFSETS[attempt],1);
    end
    repeat(4) @(posedge clk); #1;
    if(dut.tx_active || dut.csk_busy) $fatal(1,"rate=%0d not idle after sweep",RATE);
    $display("PASS tb_css_phy_tx_reset_sweep rate=%0d resets=6 plen=%0d",RATE,plen);
    $finish;
  end
  initial begin #80000000; $fatal(1,"timeout rate=%0d",RATE); end
endmodule