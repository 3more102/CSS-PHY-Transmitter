// css_dqcsk_mod.v - DQPSK differential encoder + DQCSK chirp modulator
//
// Consumes the chip stream from css_pkt_ctrl (one chip per 38-cycle window,
// four chips per chirp-symbol group) and produces the complex baseband
// sample stream:
//   - each chip pair (I,Q) maps to a QPSK symbol ((I+Q)-j(I-Q))/2
//   - a 4-lane differential encoder with exp(j*pi/4) start phase
//     (feedback memory of length 4, per IEEE 802.15.4 6.5a.2.6)
//   - each QPSK symbol rotates one 38-sample subchirp; after every group of
//     four subchirps a rate/chirp-index dependent time gap is inserted
//   - all arithmetic is exact integer replication of the MATLAB fixed-point
//     model: out = dqpsk_coef * floor(chirp * 31), coefficients in {0,+1,-1}
module css_dqcsk_mod (
    input  wire       clk,
    input  wire       rst_n,
    // configuration
    input  wire [1:0] chirp_index,    // 0..3 => m = 1..4
    // chip stream from css_pkt_ctrl
    input  wire       busy,           // packet in progress (chip bus valid)
    input  wire [1:0] chip_bus,       // {I bit, Q bit}
    input  wire       chip_last,
    output wire       chip_advance,    // one-cycle-early advance request to pkt_ctrl
    // complex sample output, one sample per clock
    output reg signed [6:0] o_i,
    output reg signed [6:0] o_q,
    output reg              o_valid,
    output reg              o_sop,
    output reg              o_eop
);

    localparam integer TSUB = 38;
    localparam M_IDLE = 2'd0, M_PLAY = 2'd1, M_GAP = 2'd2;

    reg [1:0] state;
    reg [5:0] play_cnt;
    reg [6:0] gap_cnt;
    reg [6:0] gap_len;

    reg        busy_d;
    reg [1:0]  chip_r;      // chip currently being played
    reg        last_r;      // chip_r is the final chip of the packet
    reg [1:0]  lane;        // subchirp position of chip_r within its group
    reg [2:0]  cum [0:3];   // differential encoder lanes, units of 45 deg
    reg [2:0]  u_cur;      // rotation of chip_r = 1 + cum[lane] (mod 8)
    reg        grp_odd;     // gap parity toggle
    reg        final_gap;   // current gap follows the last chirp symbol

    // ------------------------------------------------------------------
    // configuration latching + gap geometry
    // ------------------------------------------------------------------
    reg [6:0] gap_lo, gap_hi;
    always @* begin
        case (chirp_index)
            2'd0: begin gap_lo = 7'd10; gap_hi = 7'd70; end  // Tau = 15
            2'd1: begin gap_lo = 7'd20; gap_hi = 7'd60; end  // Tau = 10
            2'd2: begin gap_lo = 7'd30; gap_hi = 7'd50; end  // Tau = 5
            default: begin gap_lo = 7'd40; gap_hi = 7'd40; end // Tau = 0
        endcase
    end

    // ------------------------------------------------------------------
    // QPSK -> differential step (units of 45 deg):
    //   s = ((I+Q) - j(I-Q))/2 : (I,Q)=(1,1)->+1, (0,1)->+j, (1,0)->-j,
    //   (0,0)->-1 ; steps 0, +2, -2(+8=6), +4 respectively
    // ------------------------------------------------------------------
    function [2:0] step_of;
        input [1:0] c;
        case (c)
            2'b11: step_of = 3'd0;
            2'b01: step_of = 3'd2;
            2'b10: step_of = 3'd6;
            default: step_of = 3'd4;
        endcase
    endfunction

    wire [2:0] step_new = step_of(chip_bus);
    wire [1:0] lane_new = lane + 2'd1;
    wire [2:0] u_new    = 3'd1 + cum[lane_new] + step_new;   // mod 8

    // advance request to pkt_ctrl: fired one cycle before chip consumption
    // so the controller swaps chip_bus in time for the end-of-window latch
    wire adv_int = (state == M_PLAY) && (play_cnt == TSUB - 2) &&
                   busy && !last_r;
    assign chip_advance = adv_int;

    // chip actually consumed at the last cycle of its window
    wire consume = (state == M_PLAY) && (play_cnt == TSUB - 1) &&
                   busy && !last_r;

    // ------------------------------------------------------------------
    // sequencing
    // ------------------------------------------------------------------
    wire begin_pkt = busy && !busy_d && (state == M_IDLE);
    wire grp_done  = (lane_new == 2'd0);   // next chip starts a new group

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state    <= M_IDLE;
            play_cnt <= 6'd0;
            gap_cnt  <= 7'd0;
            gap_len  <= 7'd0;
            busy_d   <= 1'b0;
            chip_r   <= 2'd0;
            last_r   <= 1'b0;
            lane     <= 2'd0;
            u_cur    <= 3'd0;
            grp_odd  <= 1'b0;
            final_gap<= 1'b0;
            cum[0] <= 3'd0; cum[1] <= 3'd0; cum[2] <= 3'd0; cum[3] <= 3'd0;
        end else begin
            busy_d <= busy;
            case (state)
                M_IDLE: begin
                    if (begin_pkt) begin
                        chip_r <= chip_bus;
                        last_r <= chip_last;
                        lane   <= 2'd0;
                        cum[0] <= cum[0] + step_of(chip_bus);
                        u_cur  <= 3'd1 + cum[0] + step_of(chip_bus);
                        grp_odd<= 1'b0;
                        final_gap <= 1'b0;
                        state  <= M_PLAY;
                        play_cnt <= 6'd0;
                    end
                end
                M_PLAY: begin
                    if (play_cnt == TSUB - 1) begin
                        if (last_r) begin
                            state      <= M_GAP;
                            gap_cnt    <= 7'd0;
                            gap_len    <= grp_odd ? gap_hi : gap_lo;
                            final_gap  <= 1'b1;
                        end else begin
                            // consume next chip
                            chip_r       <= chip_bus;
                            last_r       <= chip_last;
                            lane         <= lane_new;
                            cum[lane_new]<= cum[lane_new] + step_new;
                            u_cur        <= u_new[2:0];
                            if (grp_done) begin
                                state   <= M_GAP;
                                gap_cnt <= 7'd0;
                                gap_len <= grp_odd ? gap_hi : gap_lo;
                                grp_odd <= ~grp_odd;
                            end
                            play_cnt <= 6'd0;
                        end
                    end else begin
                        play_cnt <= play_cnt + 6'd1;
                    end
                end
                M_GAP: begin
                    if (gap_cnt == gap_len - 7'd1) begin
                        if (final_gap)
                            state <= M_IDLE;
                        else begin
                            state <= M_PLAY;
                            play_cnt <= 6'd0;
                        end
                    end else begin
                        gap_cnt <= gap_cnt + 7'd1;
                    end
                end
                default: state <= M_IDLE;
            endcase
        end
    end

    // ------------------------------------------------------------------
    // datapath: chirp ROM fetch -> complex rotate -> output pipeline
    //
    // cycle t   : ROM address issued (sample n = play_cnt)
    // cycle t+1 : ROM data valid, products computed and registered
    // cycle t+2 : product drives the outputs; o_valid aligned via delay line
    // ------------------------------------------------------------------
    // produce covers both subchirp playback and time-gap cycles: the
    // reference model emits zero-valued samples during the gaps
    wire produce = (state == M_PLAY) || (state == M_GAP);
    wire gap_zero = (state == M_GAP);

    wire [15:0] rom_q;

    css_chirp_rom u_rom (
        .clk  (clk),
        .bank (chirp_index),
        .sub  (lane),
        .n    (play_cnt),
        .q    (rom_q)
    );

    wire signed [5:0] sr = rom_q[13:8];
    wire signed [5:0] si = rom_q[5:0];

    // rotation coefficient a + jb from phase unit u (cos/sin rounded to -1/0/1).
    // The phase is pipeline-registered alongside the ROM data so the last
    // sample of a window is multiplied with its own chip's rotation.
    reg [2:0]  u_d1;
    reg signed [1:0] ca, cb;
    always @(posedge clk) begin
        u_d1 <= u_cur;
    end
    always @* begin
        case (u_d1)
            3'd0: begin ca = 2'sd1;  cb = 2'sd0;  end
            3'd1: begin ca = 2'sd1;  cb = 2'sd1;  end
            3'd2: begin ca = 2'sd0;  cb = 2'sd1;  end
            3'd3: begin ca = -2'sd1; cb = 2'sd1;  end
            3'd4: begin ca = -2'sd1; cb = 2'sd0;  end
            3'd5: begin ca = -2'sd1; cb = -2'sd1; end
            3'd6: begin ca = 2'sd0;  cb = -2'sd1; end
            default: begin ca = 2'sd1; cb = -2'sd1; end
        endcase
    end

    // stage 1: multiply (registered)
    reg signed [6:0] p_i, p_q;
    always @(posedge clk) begin
        p_i <= ca * sr - cb * si;
        p_q <= ca * si + cb * sr;
    end

    // stage 2: output registers + alignment delay lines
    reg v_d1, v_d2, sop_evt, e_d1, e_d2;
    reg sop_d1, sop_d2;
    reg z_d1, z_d2;
    reg first_chip;

    wire sop_event = first_chip && (state == M_PLAY);
    // eop marks the final gap's last cycle: the reference stream includes
    // every zero sample of the closing time gap
    wire eop_event = final_gap && (state == M_GAP) && (gap_cnt == gap_len - 7'd1);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            v_d1 <= 1'b0; v_d2 <= 1'b0;
            sop_d1 <= 1'b0; sop_d2 <= 1'b0;
            e_d1 <= 1'b0; e_d2 <= 1'b0;
            z_d1 <= 1'b0; z_d2 <= 1'b0;
            first_chip <= 1'b0;
            o_i <= 7'sd0; o_q <= 7'sd0;
            o_valid <= 1'b0; o_sop <= 1'b0; o_eop <= 1'b0;
        end else begin
            v_d1   <= produce;
            v_d2   <= v_d1;
            sop_d1 <= sop_event;
            sop_d2 <= sop_d1;
            e_d1   <= eop_event;
            e_d2   <= e_d1;
            z_d1   <= gap_zero;
            z_d2   <= z_d1;

            o_valid <= v_d2;
            o_sop   <= sop_d2;
            o_eop   <= e_d2;
            o_i     <= (v_d2 && !z_d2) ? p_i : 7'sd0;
            o_q     <= (v_d2 && !z_d2) ? p_q : 7'sd0;

            if (begin_pkt)
                first_chip <= 1'b1;
            else if (consume)
                first_chip <= 1'b0;
        end
    end

endmodule
