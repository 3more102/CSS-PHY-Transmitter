`timescale 1ns/1ps
module tb_css_phy_tx_multi;
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
  integer pfd,sfd,rc,k,tmp,count,dones,packet;
  logic [7:0] exp_r,exp_i;
  reg [1023:0] p1_path,p2_path,p3_path,s1_path,s2_path,s3_path;
  integer pkt_len[1:3];
  reg [1023:0] pkt_payload[1:3],pkt_samples[1:3];
  always #5 clk=~clk;

  css_phy_tx_top #(.DATA_RATE(RATE),.CHIRP_INDEX(1)) dut(
    .clk(clk),.reset(reset),.start_Tx(start_Tx),.payloadLength(payloadLength),
    .payload_wr_en(payload_wr_en),.payload_addr(payload_addr),.payload_din(payload_din),
    .done_Tx(done_Tx),.Tx_real(Tx_real),.Tx_imag(Tx_imag));

  task automatic load_and_start(input integer plen,input reg [1023:0] ppath);
    begin
      payloadLength=plen[7:0];
      if(plen>0) begin
        pfd=$fopen(ppath,"r"); if(!pfd)$fatal(1,"cannot open payload file");
        for(k=0;k<plen;k=k+1) begin
          rc=$fscanf(pfd,"%h\n",tmp); if(rc!=1)$fatal(1,"short payload file");
          @(negedge clk); payload_addr=k[6:0]; payload_din=tmp[7:0]; payload_wr_en=1;
          @(posedge clk); #1; payload_wr_en=0;
        end
        $fclose(pfd);
      end
      @(negedge clk); start_Tx=1; @(negedge clk); start_Tx=0;
    end
  endtask

  task automatic check_stream(input integer plen,input reg [1023:0] spath);
    integer seen_done_cycles;
    begin
      sfd=$fopen(spath,"r"); if(!sfd)$fatal(1,"cannot open sample vector");
      count=0; seen_done_cycles=0;
      forever begin
        @(posedge clk); #1;
        if(dut.sample_valid_int) begin
          if(!dut.tx_active)$fatal(1,"rate=%0d pkt%0d: sample_valid outside active packet",RATE,packet);
          rc=$fscanf(sfd,"%h %h\n",exp_r,exp_i);
          if(rc!=2)$fatal(1,"rate=%0d pkt%0d: unexpected extra sample at %0d",RATE,packet,count);
          if(Tx_real!==exp_r || Tx_imag!==exp_i)
            $fatal(1,"rate=%0d pkt%0d mismatch sample=%0d exp=%h,%h got=%h,%h",
                   RATE,packet,count,exp_r,exp_i,Tx_real,Tx_imag);
          count=count+1;
        end else if(count>0 && !done_Tx && dut.tx_active) begin
          $fatal(1,"rate=%0d pkt%0d: sample stream bubble after sample %0d",RATE,packet,count);
        end
        if(done_Tx) begin
          seen_done_cycles=seen_done_cycles+1;
          if(seen_done_cycles>1)$fatal(1,"rate=%0d pkt%0d: done_Tx pulsed more than once",RATE,packet);
          rc=$fscanf(sfd,"%h %h\n",exp_r,exp_i); if(rc==2)$fatal(1,"rate=%0d pkt%0d: done before vector EOF",RATE,packet);
          $fclose(sfd);
          dones=dones+1;
          if(dones!=packet)$fatal(1,"rate=%0d: done count %0d out of sequence at packet %0d",RATE,dones,packet);
          return;
        end
      end
    end
  endtask

  initial begin
    if(!$value$plusargs("P1LEN=%d",pkt_len[1]))$fatal(1,"P1LEN required");
    if(!$value$plusargs("P2LEN=%d",pkt_len[2]))$fatal(1,"P2LEN required");
    if(!$value$plusargs("P3LEN=%d",pkt_len[3]))$fatal(1,"P3LEN required");
    if(!$value$plusargs("P1PAYLOAD=%s",p1_path))$fatal(1,"P1PAYLOAD required");
    if(!$value$plusargs("P2PAYLOAD=%s",p2_path))$fatal(1,"P2PAYLOAD required");
    if(!$value$plusargs("P3PAYLOAD=%s",p3_path))$fatal(1,"P3PAYLOAD required");
    if(!$value$plusargs("P1SAMPLES=%s",s1_path))$fatal(1,"P1SAMPLES required");
    if(!$value$plusargs("P2SAMPLES=%s",s2_path))$fatal(1,"P2SAMPLES required");
    if(!$value$plusargs("P3SAMPLES=%s",s3_path))$fatal(1,"P3SAMPLES required");
    pkt_payload[1]=p1_path; pkt_payload[2]=p2_path; pkt_payload[3]=p3_path;
    pkt_samples[1]=s1_path; pkt_samples[2]=s2_path; pkt_samples[3]=s3_path;

    reset=1; repeat(2)@(posedge clk); reset=0;
    dones=0;

    for(packet=1;packet<=3;packet=packet+1) begin
      load_and_start(pkt_len[packet],pkt_payload[packet]);
      check_stream(pkt_len[packet],pkt_samples[packet]);
    end

    repeat(8)@(posedge clk);
    if(dut.sample_valid_int || dut.tx_active || dut.controller_busy || dut.csk_busy || done_Tx)
      $fatal(1,"rate=%0d: transmitter not idle after third packet",RATE);
    $display("PASS tb_css_phy_tx_multi rate=%0d packets=3 lens=%0d,%0d,%0d",
             RATE,pkt_len[1],pkt_len[2],pkt_len[3]);
    $finish;
  end
  initial begin #60000000; $fatal(1,"timeout after %0d completed packets",dones); end
endmodule
