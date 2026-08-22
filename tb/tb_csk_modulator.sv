`timescale 1ns/1ps
module tb_csk_modulator;
  logic clk=0,reset=0,group_valid=0,group_ready,group_odd=0;
  logic [2:0] chirp_index=3'd1;
  logic signed [2:0] r0,i0,r1,i1,r2,i2,r3,i3;
  logic busy,sample_valid,group_done;
  logic signed [7:0] sample_real,sample_imag;
  logic [7:0] exp_r,exp_i;
  integer fd,rc,count,done_count;
  logic started;
  always #5 clk=~clk;
  csk_modulator dut(.clk(clk),.reset(reset),.sample_ce(1'b1),.group_valid(group_valid),.group_ready(group_ready),
    .chirp_index(chirp_index),.group_odd(group_odd),
    .s0_real(r0),.s0_imag(i0),.s1_real(r1),.s1_imag(i1),.s2_real(r2),.s2_imag(i2),.s3_real(r3),.s3_imag(i3),
    .busy(busy),.sample_valid(sample_valid),.sample_real(sample_real),.sample_imag(sample_imag),.group_done(group_done));

  task automatic enqueue_group(input bit odd,input integer a0,input integer b0,input integer a1,input integer b1,
                               input integer a2,input integer b2,input integer a3,input integer b3);
    begin
      while(!group_ready) @(negedge clk);
      @(negedge clk); group_odd=odd; r0=a0; i0=b0; r1=a1; i1=b1; r2=a2; i2=b2; r3=a3; i3=b3; group_valid=1;
      @(posedge clk); #1; group_valid=0;
    end
  endtask

  initial begin
    fd=$fopen("vectors/csk_m1_two_groups.hex","r"); if(!fd)$fatal(1,"cannot open CSK vector");
    reset=1; repeat(2) @(posedge clk); reset=0;
    fork
      begin
        enqueue_group(0, 1,1, 1,-1, -1,1, -1,-1);
        enqueue_group(1, -1,1, 1,1, 1,-1, -1,-1);
      end
      begin
        count=0; done_count=0; started=0;
        forever begin
          @(posedge clk); #1;
          if(sample_valid) begin
            started=1;
            rc=$fscanf(fd,"%h %h\n",exp_r,exp_i);
            if(rc!=2)$fatal(1,"unexpected extra CSK sample %0d",count);
            if(sample_real!==exp_r || sample_imag!==exp_i)
              $fatal(1,"CSK sample=%0d exp=%h,%h got=%h,%h",count,exp_r,exp_i,sample_real,sample_imag);
            count=count+1;
          end else if(started && count<384) begin
            $fatal(1,"sample_valid bubble at sample count %0d",count);
          end
          if(group_done) done_count=done_count+1;
          if(started && count==384 && !busy) begin
            if(done_count!=2)$fatal(1,"expected two group_done pulses got %0d",done_count);
            rc=$fscanf(fd,"%h %h\n",exp_r,exp_i);
            if(rc==2)$fatal(1,"vector has unexpected trailing data");
            $fclose(fd); $display("PASS tb_csk_modulator"); $finish;
          end
        end
      end
    join
  end
  initial begin #20000; $fatal(1,"timeout"); end
endmodule
