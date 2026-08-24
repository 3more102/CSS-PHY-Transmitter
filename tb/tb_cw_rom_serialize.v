// tb_cw_rom_serialize.v - exhaustive unit test for css_codeword_rom
//
// For every reachable data symbol it captures the SERIALIZED chip sequence
// (bit 0 first, exactly as css_pkt_ctrl consumes buf[ser_cnt]) and writes it
// to cw_serialized.txt as:
//   <rate> <symbol> <chip c0> <chip c1> ...
// Verification against the MATLAB/reference tables is done by
// scripts/check_cw_serialization.py.
`timescale 1ns/1ps

module tb_cw_rom_serialize;

    reg         clk = 0;
    reg         rate = 0;
    reg  [8:0]  addr = 0;
    wire [31:0] cw;

    css_codeword_rom dut (.clk(clk), .rate(rate), .addr(addr), .cw(cw));

    always #5 clk = ~clk;

    integer fd;
    integer sym, k;
    reg [31:0] word;

    initial begin
        fd = $fopen("cw_serialized.txt", "w");
        // rate 0: all 8 input symbols
        rate = 1'b0;
        for (sym = 0; sym < 8; sym = sym + 1) begin
            @(negedge clk); addr = sym;
            @(posedge clk); #1;                 // registered read done
            word = cw;
            $fwrite(fd, "0 %0d", sym);
            for (k = 0; k < 4; k = k + 1)
                $fwrite(fd, " %0d", word[k]);   // bit 0 first == c0 first
            $fwrite(fd, "\n");
        end
        // rate 1: all 64 reachable 6-bit input symbols
        rate = 1'b1;
        for (sym = 0; sym < 64; sym = sym + 1) begin
            @(negedge clk); addr = sym;
            @(posedge clk); #1;
            word = cw;
            $fwrite(fd, "1 %0d", sym);
            for (k = 0; k < 32; k = k + 1)
                $fwrite(fd, " %0d", word[k]);
            $fwrite(fd, "\n");
        end
        $fclose(fd);
        $display("TB RESULT: DUMP COMPLETE (%0d rows)", 8 + 64);
        $finish;
    end
endmodule
