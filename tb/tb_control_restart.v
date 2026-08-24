// tb_control_restart.v - control/restart coverage for css_tx_top
//
// Explicitly exercises what the single-packet regression does not:
//   phase 1 : full packet, exact stream check (rate0 / len20 / m1)
//   phase 2 : SECOND packet started back-to-back WITHOUT reset, with a
//             different data rate, chirp index and length
//             (rate1 / len25 / m2) - covers controller return-to-idle,
//             done (eop + busy fall), and rate change between packets
//   phase 3 : reset applied MID-PACKET, then a fresh short packet
//             (rate0 / len3 / m1) must still be bit-exact - covers reset
//             recovery of both FSMs, payload RAM rewrite pointer and
//             differential-encoder lanes
//
// Plusargs:
//   +p1=<payload hex> +g1=<golden hex> +n1=<samples>
//   +r1=<0|1> +m1=<1..4> +l1=<bytes>
//   same set with suffix 2 and 3
`timescale 1ns/1ps

module tb_control_restart;

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
        .clk(clk), .rst_n(rst_n), .start(start),
        .data_rate(data_rate), .chirp_index(chirp_index),
        .payload_len(payload_len),
        .payload_ready(payload_ready),
        .payload_valid(payload_valid), .payload_data(payload_data),
        .o_i(o_i), .o_q(o_q), .o_valid(o_valid),
        .o_sop(o_sop), .o_eop(o_eop)
    );

    always #5 clk = ~clk;

    integer errors = 0;

    reg [255:8] s;
    reg [7:0]   pbytes [0:126];
    reg [15:0]  gmem [0:MAXSAMP];

    integer i, idx, guard;
    integer dummy;
    integer n1, n2, n3, m1, m2, m3, l1, l2, l3, r1, r2, r3;
    integer gi, gq;
    reg got_sop, got_eop;

    task load_payload(input [255:8] fname);
        begin
            for (i = 0; i < 127; i = i + 1) pbytes[i] = 8'h00;
            $readmemh(fname, pbytes);
        end
    endtask

    task load_golden(input [255:8] fname);
        begin
            for (i = 0; i < MAXSAMP + 1; i = i + 1) gmem[i] = 16'hxxxx;
            $readmemh(fname, gmem);
        end
    endtask

    // preload payload bytes before start (same protocol as tb_css_tx_top)
    task preload(input integer n);
        begin
            for (i = 0; i < n; i = i + 1) begin
                @(negedge clk);
                payload_valid = 1'b1;
                payload_data  = pbytes[i];
                @(posedge clk);
            end
            @(negedge clk);
            payload_valid = 1'b0;
        end
    endtask

    // launch one packet and verify its complete output stream
    task run_packet(input r, input integer m, input integer len,
                    input integer nsamp, input [255:8] label);
        begin
            data_rate   = r;
            chirp_index = m[1:0] - 2'd1;   // plusarg m is 1-based
            payload_len = len[6:0];
            repeat (2) @(negedge clk);
            start = 1'b1;
            @(negedge clk);
            start = 1'b0;

            idx = 0; got_sop = 0; got_eop = 0; guard = 0;
            while (!got_eop && guard < 4 * nsamp + 100000) begin
                @(posedge clk);
                guard = guard + 1;
                if (o_valid === 1'b1) begin
                    gi = $signed(gmem[idx][15:8]);
                    gq = $signed(gmem[idx][7:0]);
                    if ({gi[6:0], gq[6:0]} !== {o_i, o_q}) begin
                        if (errors < 20)
                            $display("TB ERROR [%0s]: sample %0d: got (%0d,%0d) expected (%0d,%0d)",
                                     label, idx, o_i, o_q, gi, gq);
                        errors = errors + 1;
                    end
                    if (o_sop && idx != 0 && !got_sop) begin
                        $display("TB ERROR [%0s]: unexpected sop at %0d", label, idx);
                        errors = errors + 1;
                    end
                    if (o_sop) got_sop = 1'b1;
                    if (o_eop) got_eop = 1'b1;
                    idx = idx + 1;
                end else if (o_valid !== 1'b0 && o_valid !== 1'b1) begin
                    $display("TB ERROR [%0s]: o_valid is X at cycle %0d", label, guard);
                    errors = errors + 1;
                end
            end

            if (!got_sop) begin $display("TB ERROR [%0s]: sop never asserted", label); errors = errors + 1; end
            if (!got_eop) begin $display("TB ERROR [%0s]: eop missing", label); errors = errors + 1; end
            if (idx !== nsamp) begin
                $display("TB ERROR [%0s]: sample count %0d != expected %0d", label, idx, nsamp);
                errors = errors + 1;
            end

            // done_Tx semantics: busy must fall after eop
            guard = 0;
            while (dut.busy !== 1'b0 && guard < 1000) begin
                @(posedge clk); guard = guard + 1;
            end
            if (dut.busy !== 1'b0) begin
                $display("TB ERROR [%0s]: busy did not fall after eop", label);
                errors = errors + 1;
            end

            // idle quiescence: no stray samples after done
            repeat (200) begin
                @(posedge clk);
                if (o_valid !== 1'b0) begin
                    $display("TB ERROR [%0s]: stray o_valid after eop", label);
                    errors = errors + 1;
                end
            end
        end
    endtask

    // ------------------------------------------------------------------
    initial begin
        dummy = $value$plusargs("p1=%s", s);
        load_payload(s);
        dummy = $value$plusargs("g1=%s", s);
        load_golden(s);
        dummy = $value$plusargs("n1=%d", n1);
        dummy = $value$plusargs("m1=%d", m1);
        dummy = $value$plusargs("l1=%d", l1);
        dummy = $value$plusargs("r1=%d", r1);

        // reset
        rst_n = 1'b0;
        repeat (5) @(posedge clk);
        rst_n = 1'b1;
        repeat (2) @(posedge clk);

        preload(l1);
        run_packet(r1[0], m1, l1, n1, "pkt1");
        $display("TB INFO: packet 1 verified (%0d samples)", n1);

        // ---- phase 2: second packet WITHOUT any reset -----------------
        dummy = $value$plusargs("p2=%s", s);
        if (!dummy) begin $display("TB ERROR: missing +p2"); $finish; end
        load_payload(s);
        dummy = $value$plusargs("g2=%s", s);
        if (!dummy) begin $display("TB ERROR: missing +g2"); $finish; end
        load_golden(s);
        dummy = $value$plusargs("n2=%d", n2);
        dummy = $value$plusargs("m2=%d", m2);
        dummy = $value$plusargs("l2=%d", l2);
        dummy = $value$plusargs("r2=%d", r2);

        preload(l2);
        run_packet(r2[0], m2, l2, n2, "pkt2");
        $display("TB INFO: packet 2 verified back-to-back (%0d samples)", n2);

        // ---- phase 3: mid-packet reset, then restart ------------------
        dummy = $value$plusargs("p3=%s", s);
        if (!dummy) begin $display("TB ERROR: missing +p3"); $finish; end
        dummy = $value$plusargs("g3=%s", s);
        if (!dummy) begin $display("TB ERROR: missing +g3"); $finish; end
        dummy = $value$plusargs("n3=%d", n3);
        dummy = $value$plusargs("m3=%d", m3);
        dummy = $value$plusargs("l3=%d", l3);
        dummy = $value$plusargs("r3=%d", r3);

        // start an aborted long packet purely to disturb internal state,
        // then hit reset while chips are streaming
        load_payload(s);           // any bytes; packet will be aborted
        data_rate   = r3[0];
        chirp_index = m3[1:0] - 2'd1;
        payload_len = 7'd127;
        repeat (2) @(negedge clk);
        start = 1'b1;
        @(negedge clk);
        start = 1'b0;
        repeat (3000) @(posedge clk);          // mid-packet
        rst_n = 1'b0;
        repeat (5) @(posedge clk);
        rst_n = 1'b1;
        repeat (4) @(posedge clk);

        // now run the real phase-3 packet and require bit-exactness
        load_payload(s);
        preload(l3);
        run_packet(r3[0], m3, l3, n3, "restart");
        $display("TB INFO: post-reset restart verified (%0d samples)", n3);

        if (errors == 0)
            $display("TB RESULT: PASS (control/restart, all phases)");
        else
            $display("TB RESULT: FAIL (errors=%0d)", errors);
        $finish;
    end

    initial begin
        #400000000;   // watchdog
        $display("TB ERROR: global watchdog timeout");
        $display("TB RESULT: FAIL (watchdog)");
        $finish;
    end

endmodule
