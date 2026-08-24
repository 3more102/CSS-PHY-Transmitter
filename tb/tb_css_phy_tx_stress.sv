`timescale 1ns/1ps
module tb_css_phy_tx_stress;
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
  integer pfd,sfd,ifd,rc,k,tmp,count,g,gap,pkt,plen,packets_done;
  logic [7:0] exp_r,exp_i;
  reg [1023:0] sched_path,rate_tag,pload_path,samp_path;
  logic done_seen;
  always #5 clk=~clk;

  css_phy_tx_top #(.DATA_RATE(RATE),.CHIRP_INDEX(1)) dut(
    .clk(clk),.reset(reset),.start_Tx(start_Tx),.payloadLength(payloadLength),
    .payload_wr_en(payload_wr_en),.payload_addr(payload_addr),.payload_din(payload_din),
    .done_Tx(done_Tx),.Tx_real(Tx_real),.Tx_imag(Tx_imag));

  task automatic expect_idle(input integer where);
    begin
      if(dut.tx_active || dut.csk_busy || dut.sample_valid_int)
        $fatal(1,"rate=%0d pkt%0d: transmitter active at checkpoint %0d",RATE,pkt,where);
      if($isunknown({Tx_real,Tx_imag,done_Tx}))
        $fatal(1,"rate=%0d pkt%0d: X/Z on observable outputs at checkpoint %0d",RATE,pkt,where);
    end
  endtask

  task automatic load_payload(input integer len);
    begin
      payloadLength=len[7:0]; payload_wr_en=0;
      if(len>0) begin
        void'($sformat(pload_path,"vectors/stress_%0s_p%0d_payload.hex",rate_tag,pkt));
        pfd=$fopen(pload_path,"r"); if(!pfd)$fatal(1,"rate=%0d pkt%0d: cannot open payload",RATE,pkt);
        for(k=0;k<len;k=k+1) begin
          rc=$fscanf(pfd,"%h\n",tmp); if(rc!=1)$fatal(1,"rate=%0d pkt%0d: short payload",RATE,pkt);
          @(negedge clk); payload_addr=k[6:0]; payload_din=tmp[7:0]; payload_wr_en=1;
          @(posedge clk); #1; payload_wr_en=0;
        end
        $fclose(pfd);
      end
    end
  endtask

  // One complete packet: golden-compare every emitted sample, require exactly
  // one done cycle with vector EOF, then hold the scheduled inter-packet idle
  // gap while asserting total output silence and known outputs.
  task automatic run_packet(input integer len,input integer gap_cycles);
    begin
      void'($sformat(samp_path,"vectors/stress_%0s_p%0d_samples.hex",rate_tag,pkt));
      sfd=$fopen(samp_path,"r"); if(!sfd)$fatal(1,"rate=%0d pkt%0d: cannot open golden samples",RATE,pkt);
      @(negedge clk); start_Tx=1; @(negedge clk); start_Tx=0;
      count=0; done_seen=0;
      while(!done_seen) begin
        @(posedge clk); #1;
        if(dut.sample_valid_int) begin
          if($isunknown({Tx_real,Tx_imag}))
            $fatal(1,"rate=%0d pkt%0d: X/Z on Tx outputs at sample %0d",RATE,pkt,count);
          rc=$fscanf(sfd,"%h %h\n",exp_r,exp_i);
          if(rc!=2)$fatal(1,"rate=%0d pkt%0d: extra sample %0d",RATE,pkt,count);
          if(Tx_real!==exp_r || Tx_imag!==exp_i)
            $fatal(1,"rate=%0d pkt%0d mismatch sample=%0d exp=%h,%h got=%h,%h",
                   RATE,pkt,count,exp_r,exp_i,Tx_real,Tx_imag);
          count=count+1;
        end else if(count>0 && !done_Tx && dut.tx_active) begin
          $fatal(1,"rate=%0d pkt%0d: stream bubble after sample %0d",RATE,pkt,count);
        end
        if(done_Tx) begin
          done_seen=1;
          rc=$fscanf(sfd,"%h %h\n",exp_r,exp_i);
          if(rc==2)$fatal(1,"rate=%0d pkt%0d: done before golden EOF",RATE,pkt);
          $fclose(sfd);
        end
      end
      packets_done=packets_done+1;
      for(g=0;g<gap_cycles;g=g+1) begin
        @(posedge clk); #1;
        if(dut.sample_valid_int || dut.tx_active || done_Tx)
          $fatal(1,"rate=%0d pkt%0d: activity during inter-packet gap cycle %0d",RATE,pkt,g);
        if($isunknown({Tx_real,Tx_imag,done_Tx}))
          $fatal(1,"rate=%0d pkt%0d: X/Z during gap cycle %0d",RATE,pkt,g);
      end
    end
  endtask

  initial begin
    if(!$value$plusargs("SCHEDULE=%s",sched_path))$fatal(1,"SCHEDULE plusarg required");
    if(!$value$plusargs("RATETAG=%s",rate_tag))$fatal(1,"RATETAG plusarg required");
    ifd=$fopen(sched_path,"r"); if(!ifd)$fatal(1,"cannot open stress schedule");
    reset=1; repeat(2)@(posedge clk); @(negedge clk); reset=0;
    packets_done=0; pkt=0;

    rc=$fscanf(ifd,"%d %d %d\n",pkt,plen,gap);
    while(rc==3) begin
      expect_idle(1);
      load_payload(plen);
      run_packet(plen,gap);
      rc=$fscanf(ifd,"%d %d %d\n",pkt,plen,gap);
    end

    repeat(4)@(posedge clk); #1;
    expect_idle(2);
    $display("PASS tb_css_phy_tx_stress rate=%0d packets=%0d",RATE,packets_done);
    $finish;
  end
  initial begin #100000000; $fatal(1,"stress timeout after %0d packets",packets_done); end
endmodule
