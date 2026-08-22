`timescale 1ns/1ps
module tb_chirp_rom;
  logic [2:0] chirp_index;
  logic [7:0] addr;
  logic signed [5:0] r,i;
  logic signed [5:0] exp_r[0:151], exp_i[0:151];
  integer k;
  chirp_rom dut(.chirp_index(chirp_index),.addr(addr),.chirp_real(r),.chirp_imag(i));
  initial begin
    $readmemb("matlab/original/chirpSequenceReal_tofile.txt",exp_r);
    $readmemb("matlab/original/chirpSequenceImag_tofile.txt",exp_i);
    chirp_index=3'd1;
    for(k=0;k<152;k=k+1) begin addr=k[7:0]; #1;
      if(r!==exp_r[k] || i!==exp_i[k]) $fatal(1,"chirp addr=%0d mismatch",k);
    end
    $display("PASS tb_chirp_rom"); $finish;
  end
endmodule
