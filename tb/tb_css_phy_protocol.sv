`timescale 1ns/1ps
module tb_css_phy_protocol;
`ifdef RATE250
  localparam integer RATE = 1;
  localparam integer EXPECTED_SAMPLES = 7680;
`else
  localparam integer RATE = 0;
  localparam integer EXPECTED_SAMPLES = 2850;
`endif

  logic clk=0, reset=0, start_Tx=0, payload_wr_en=0;
  logic [7:0] payloadLength=0;
  logic [6:0] payload_addr=0;
  logic [7:0] payload_din=0;
  logic done_Tx;
  logic signed [7:0] Tx_real, Tx_imag;
  integer samples;

  always #5 clk=~clk;

  css_phy_tx_top #(.DATA_RATE(RATE), .CHIRP_INDEX(1), .SAMPLE_DIV(1)) dut(
    .clk(clk), .reset(reset), .start_Tx(start_Tx), .payloadLength(payloadLength),
    .payload_wr_en(payload_wr_en), .payload_addr(payload_addr), .payload_din(payload_din),
    .done_Tx(done_Tx), .Tx_real(Tx_real), .Tx_imag(Tx_imag));

  task automatic pulse_start;
    begin
      @(negedge clk); start_Tx=1;
      @(negedge clk); start_Tx=0;
    end
  endtask

  task automatic sync_reset;
    begin
      @(negedge clk); reset=1;
      repeat(2) @(posedge clk);
      @(negedge clk); reset=0;
    end
  endtask

  initial begin
    sync_reset();
    payloadLength=8'd128;
    pulse_start();
    repeat(8) @(posedge clk);
    #1;
    if(dut.tx_active || dut.controller_busy || done_Tx)
      $fatal(1,"rate=%0d illegal payload length was accepted",RATE);

    payloadLength=8'd0;
    pulse_start();
    wait(dut.tx_active);
    repeat(5) @(posedge clk);
    @(negedge clk); start_Tx=1; #1;
    if(dut.controller_start)
      $fatal(1,"rate=%0d start_Tx was accepted while packet active",RATE);
    @(negedge clk); start_Tx=0;

    wait(dut.sample_valid_int);
    repeat(20) @(posedge clk);
    sync_reset();
    @(posedge clk); #1;
    if(dut.tx_active || dut.controller_busy || dut.csk_busy || done_Tx)
      $fatal(1,"rate=%0d reset did not return transmitter to idle",RATE);
    if(Tx_real!==8'sd0 || Tx_imag!==8'sd0)
      $fatal(1,"rate=%0d reset did not clear output samples",RATE);

    samples=0;
    pulse_start();
    forever begin
      @(posedge clk); #1;
      if(dut.sample_valid_int) samples=samples+1;
      if(done_Tx) begin
        if(samples!=EXPECTED_SAMPLES)
          $fatal(1,"rate=%0d restart sample count expected=%0d got=%0d",RATE,EXPECTED_SAMPLES,samples);
        break;
      end
    end

    // Held-start contract: a level start_Tx is ignored while a packet is
    // active and re-arms the transmitter immediately after done_Tx, so
    // holding it high produces identical consecutive packets.
    samples=0;
    @(negedge clk); start_Tx=1;
    wait(dut.tx_active);
    forever begin
      @(posedge clk); #1;
      if(dut.sample_valid_int) samples=samples+1;
      if(done_Tx) begin
        if(samples!=EXPECTED_SAMPLES)
          $fatal(1,"rate=%0d held-start packet expected=%0d got=%0d",RATE,EXPECTED_SAMPLES,samples);
        break;
      end
    end
    @(negedge clk); start_Tx=0;
    repeat(4) @(posedge clk); #1;
    if(dut.tx_active || dut.csk_busy || dut.sample_valid_int)
      $fatal(1,"rate=%0d not idle after dropping held start",RATE);
    $display("PASS tb_css_phy_protocol rate=%0d samples=%0d",RATE,samples);
    $finish;
  end

  initial begin #20000000; $fatal(1,"protocol timeout rate=%0d",RATE); end
endmodule
