`timescale 1ns/1ps
module tb_dqpsk_encoder;
  logic clk=0, reset=0, init_packet=0, in_valid=0, accept=1;
  logic chip_i, chip_q;
  logic signed [2:0] qr,qi,dr,di;
  logic out_valid;
  integer fd,rc,idx,vi,vq,er,ei,count;
  reg [1023:0] header_line;
  always #5 clk=~clk;
  qpsk_mapper qm(.chip_i(chip_i),.chip_q(chip_q),.qpsk_real(qr),.qpsk_imag(qi));
  dqpsk_encoder dut(.clk(clk),.reset(reset),.init_packet(init_packet),.in_valid(in_valid),.accept(accept),
    .in_real(qr),.in_imag(qi),.out_valid(out_valid),.out_real(dr),.out_imag(di));
  initial begin
    reset=1; repeat(2) @(posedge clk); reset=0;
    init_packet=1; @(posedge clk); #1; init_packet=0;
    fd=$fopen("vectors/dqpsk_unit.txt","r"); if(!fd)$fatal(1,"cannot open dqpsk vectors");
    rc=$fgets(header_line,fd);
    if(rc==0)$fatal(1,"cannot read dqpsk vector header");
    count=0;
    while(!$feof(fd)) begin
      rc=$fscanf(fd,"%d %d %d %d %d\n",idx,vi,vq,er,ei);
      if(rc==5) begin
        @(negedge clk); chip_i=(vi==1); chip_q=(vq==1); in_valid=1;
        #1;
        if(!out_valid || $signed(dr)!==er || $signed(di)!==ei)
          $fatal(1,"DQPSK idx=%0d exp=(%0d,%0d) got=(%0d,%0d)",idx,er,ei,$signed(dr),$signed(di));
        @(posedge clk); #1; in_valid=0; count=count+1;
      end
    end
    $fclose(fd); if(count!=16)$fatal(1,"expected 16 vectors got %0d",count);
    $display("PASS tb_dqpsk_encoder"); $finish;
  end
endmodule
