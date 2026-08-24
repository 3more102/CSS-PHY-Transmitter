// tb_css_tx_top.v - self-checking testbench for the CSS PHY transmitter
//
// Compares every output sample against the Python golden model
// (scripts/gen_golden_vectors.py), which is bit-exact against the MATLAB
// fixed-point reference.
//
// Plusargs:
//   +rate=<0|1>        data rate selector used in DUT config
//   +plen=<bytes>      payload length used in DUT config
//   +m=<0..3>          chirp index selector (m-1)
//   +nsamp=<samples>   expected number of output samples
//   +payload=<file>    payload stimulus bytes (hex, one byte per line)
//   +golden=<file>     expected samples (hex, II QQ per line)
//   +vcd               optional VCD dump
`timescale 1ns/1ps

module tb_css_tx_top;

    localparam integer MAXSAMP = 140000;

    reg         clk = 1'b0;
    reg         rst_n = 1'b0;
    reg         start = 1'b0;
    reg         data_rate = 1'b0;
    reg  [1:0]  chirp_index = 2'd0;
    reg  [6:0]  payload_len = 7'd1;
    reg         payload_valid = 1'b0;
    reg  [7:0]  payload_data = 8'd0;
    wire        payload_ready;
    wire signed [6:0] o_i, o_q;
    wire        o_valid, o_sop, o_eop;

    css_tx_top dut (
        .clk           (clk),
        .rst_n         (rst_n),
        .start         (start),
        .data_rate     (data_rate),
        .chirp_index   (chirp_index),
        .payload_len   (payload_len),
        .payload_ready (payload_ready),
        .payload_valid (payload_valid),
        .payload_data  (payload_data),
        .o_i           (o_i),
        .o_q           (o_q),
        .o_valid       (o_valid),
        .o_sop         (o_sop),
        .o_eop         (o_eop)
    );

    always #5 clk = ~clk;

    // ------------------------------------------------------------------
    integer errors = 0;
    integer nsamp = 0;
    integer rate_i = 0;
    integer m_i = 0;
    integer plen_i = 0;

    reg [255:8] payload_fname;
    reg [255:8] golden_fname;
    reg [255:8] out_fname;

    integer fout;

    reg [7:0]  pbytes [0:126];
    reg [15:0] gmem [0:MAXSAMP];

    integer i, idx;
    integer gi, gq;
    integer guard;
    reg got_sop, got_eop;

    initial begin
        if (!$value$plusargs("rate=%d", rate_i))  begin $display("TB ERROR: missing +rate");  $finish; end
        if (!$value$plusargs("plen=%d", plen_i))  begin $display("TB ERROR: missing +plen");  $finish; end
        if (!$value$plusargs("m=%d", m_i))        begin $display("TB ERROR: missing +m");      $finish; end
        if (!$value$plusargs("nsamp=%d", nsamp))  begin $display("TB ERROR: missing +nsamp"); $finish; end
        if (!$value$plusargs("payload=%s", payload_fname)) begin $display("TB ERROR: missing +payload"); $finish; end
        if (!$value$plusargs("golden=%s", golden_fname))   begin $display("TB ERROR: missing +golden");  $finish; end

        $readmemh(payload_fname, pbytes);
        for (i = 0; i < MAXSAMP + 1; i = i + 1)
            gmem[i] = 16'hxxxx;
        $readmemh(golden_fname, gmem);

        $display("TB INFO: rate=%0d plen=%0d m=%0d nsamp=%0d",
                 rate_i, plen_i, m_i, nsamp);

        // reset
        rst_n = 1'b0;
        repeat (5) @(posedge clk);
        rst_n = 1'b1;
        repeat (2) @(posedge clk);

        // preload payload bytes
        // preload payload bytes: drive each byte for exactly one posedge
        for (i = 0; i < plen_i; i = i + 1) begin
            @(negedge clk);
            payload_valid = 1'b1;
            payload_data  = pbytes[i];
            @(posedge clk);                      // DUT samples the byte here
        end
        @(negedge clk);
        payload_valid = 1'b0;

        // configure and launch
        data_rate    = rate_i[0];
        chirp_index  = m_i[1:0] - 2'd1;   // plusarg m is 1-based (m = 1..4)
        payload_len  = plen_i[6:0];
        repeat (2) @(negedge clk);
        start = 1'b1;
        @(negedge clk);
        start = 1'b0;

        if ($test$plusargs("vcd")) begin
            $dumpfile("tb_css_tx_top.vcd");
            $dumpvars(0, tb_css_tx_top);
        end

        if ($value$plusargs("dump_out=%s", out_fname))
            fout = $fopen(out_fname, "w");
        else
            fout = 0;

        // collect and check
        idx = 0;
        got_sop = 1'b0;
        got_eop = 1'b0;
        guard = 0;
        while (!got_eop && guard < 4 * nsamp + 100000) begin
            @(posedge clk);
            guard = guard + 1;
            if (o_valid !== 1'b1) begin
                if (idx > 0 && o_valid !== 1'b0) begin
                    $display("TB ERROR: o_valid is X at sample %0d", idx);
                    errors = errors + 1;
                end
            end else begin
                if (fout)
                    $fwrite(fout, "%02x%02x\n", o_i, o_q);
                gi = $signed(gmem[idx][15:8]);
                gq = $signed(gmem[idx][7:0]);
                if ({gi[6:0], gq[6:0]} !== {o_i, o_q}) begin
                    if (errors < 10)
                        $display("TB ERROR: sample %0d: got (%0d,%0d) expected (%0d,%0d)",
                                 idx, o_i, o_q, gi, gq);
                    errors = errors + 1;
                end
                if (o_sop && idx != 0 && !got_sop) begin
                    $display("TB ERROR: unexpected sop at sample %0d", idx);
                    errors = errors + 1;
                end
                if (o_sop) got_sop = 1'b1;
                if (o_eop) got_eop = 1'b1;
                idx = idx + 1;
            end
        end

        if (!got_eop)
            $display("TB ERROR: timeout / missing eop after %0d samples", idx);
        if (!got_sop)
            $display("TB ERROR: sop never asserted");
        if (idx !== nsamp) begin
            $display("TB ERROR: sample count %0d != expected %0d", idx, nsamp);
            errors = errors + 1;
        end

        if (errors == 0 && got_sop && got_eop && idx == nsamp)
            $display("TB RESULT: PASS (%0d samples verified)", nsamp);
        else
            $display("TB RESULT: FAIL (errors=%0d samples=%0d)", errors, idx);

        $finish;
    end

    // global watchdog
    initial begin
        #100000000;   // 100 ms sim time = 10M clocks
        $display("TB ERROR: global watchdog timeout");
        $display("TB RESULT: FAIL (watchdog)");
        $finish;
    end

endmodule
