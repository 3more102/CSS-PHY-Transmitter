`timescale 1ns/1ps
module tb_dqpsk_encoder;
  logic clk=0, reset=0, init_packet=0, in_valid=0, accept=1;
  logic chip_i, chip_q;
  logic signed [2:0] qr,qi,dr,di;
  logic out_valid;
  integer fd,rc,idx,vi,vq,er,ei,count,expected;
  reg [1023:0] header_line;
  always #5 clk=~clk;
  qpsk_mapper qm(.chip_i(chip_i),.chip_q(chip_q),.qpsk_real(qr),.qpsk_imag(qi));
  dqpsk_encoder dut(.clk(clk),.reset(reset),.init_packet(init_packet),.in_valid(in_valid),.accept(accept),
    .in_real(qr),.in_imag(qi),.out_valid(out_valid),.out_real(dr),.out_imag(di));

  // Stream one reference row through QPSK+DQPSK and compare combinationally.
  task automatic check_row;
    begin
      @(negedge clk); chip_i=(vi==1); chip_q=(vq==1); in_valid=1;
      #1;
      if(!out_valid || $signed(dr)!==er || $signed(di)!==ei)
        $fatal(1,"DQPSK idx=%0d exp=(%0d,%0d) got=(%0d,%0d)",idx,er,ei,$signed(dr),$signed(di));
      @(posedge clk); #1; in_valid=0; count=count+1;
    end
  endtask

  // Open a DQPSK vector file and consume its two-line header
  // ("IDX I Q OUT_REAL OUT_IMAG" then the exact expected row count).
  task automatic open_vector(input [1023:0] path);
    begin
      fd=$fopen(path,"r"); if(!fd)$fatal(1,"cannot open %0s",path);
      rc=$fgets(header_line,fd);
      if(rc==0)$fatal(1,"cannot read DQPSK vector header");
      rc=$fscanf(fd,"%d\n",expected);
      if(rc!=1 || expected<=0)$fatal(1,"missing/bad row count in %0s",path);
      count=0;
    end
  endtask

  initial begin
    reset=1; repeat(2) @(posedge clk); reset=0;

    // Phase 1: directed unit stimulus.
    init_packet=1; @(posedge clk); #1; init_packet=0;
    open_vector("vectors/dqpsk_unit.txt");
    while(!$feof(fd)) begin
      rc=$fscanf(fd,"%d %d %d %d %d\n",idx,vi,vq,er,ei);
      if(rc==5) check_row();
    end
    $fclose(fd);
    if(count!=expected)$fatal(1,"unit vector: expected %0d vectors got %0d",expected,count);

    // Phase 2: exhaustive differential-transition stimulus. Every reachable
    // feedback value x input symbol product is visited (4x4) plus every
    // initial-seed product (1+1j x4). A fresh init_packet isolates phases so
    // packet-reset semantics are exercised between them.
    init_packet=1; @(posedge clk); #1; init_packet=0;
    open_vector("vectors/dqpsk_transitions.txt");
    while(!$feof(fd)) begin
      rc=$fscanf(fd,"%d %d %d %d %d\n",idx,vi,vq,er,ei);
      if(rc==5) check_row();
    end
    $fclose(fd);
    if(count!=expected)$fatal(1,"transition vector: expected %0d vectors got %0d",expected,count);

    $display("PASS tb_dqpsk_encoder"); $finish;
  end
endmodule
