// css_pkt_ctrl.v - CSS PHY packet chip generator
//
// Builds the complete chip-level I/Q stream for one packet:
//   preamble -> SFD -> [PHR | payload | padding] demuxed to I/Q paths,
//   data-symbol mapping onto bi-orthogonal codewords (c0 serialized first),
//   with the 250 kb/s bit interleaver applied across pairs of codewords.
//
// The consumer (css_dqcsk_mod) paces the bus with `chip_latch` pulses
// (one pulse in the last cycle of every 38-cycle chip window).  The chip
// on chip_bus is consumed at each pulse; the controller presents the next
// chip immediately after the pulse edge.
module css_pkt_ctrl #(
    parameter integer PAYLOAD_MAX = 127
) (
    input  wire       clk,
    input  wire       rst_n,
    // configuration / stimulus
    input  wire       start,          // one-cycle pulse
    input  wire       data_rate,      // 0 = 1 Mb/s, 1 = 250 kb/s
    input  wire [6:0] payload_len,    // payload bytes, 1..127
    output wire       payload_ready,
    input  wire       payload_valid,
    input  wire [7:0] payload_data,
    // pacing from modulator
    input  wire       chip_latch,     // consume current chip_bus now
    // chip stream to modulator
    output reg        busy,
    output wire       chip_valid,
    output wire [1:0] chip_bus,       // {I bit, Q bit}, 1 => +1
    output wire       chip_last
);

    localparam integer PHR_BITS = 12;
    localparam integer BPC1 = 6;     // bits per codeword, 250 kb/s

    // SFD tables (Table 20a), bit index = chip index:
    //   1 Mb/s   chips 0 1 1 1 0 1 0 0 1 0 0 1 1 1 0 0
    //   250 kb/s chips 0 1 1 1 1 0 1 0 0 0 1 0 0 0 1 1
    localparam [15:0] SFD_1M   = 16'b0011_1001_0010_1110;
    localparam [15:0] SFD_250K = 16'b1100_0100_0101_1110;

    // ------------------------------------------------------------------
    // declarations
    // ------------------------------------------------------------------
    reg [7:0]  ram [0:PAYLOAD_MAX-1];
    reg [6:0]  wr_ptr;

    localparam ST_IDLE = 2'd0,
               ST_CFG  = 2'd1,
               ST_RUN  = 2'd2;
    reg [1:0]  st;
    reg        r_rate;
    reg [6:0]  r_len;

    localparam PH_PRE  = 2'd0,
               PH_SFD  = 2'd1,
               PH_DATA = 2'd2;
    reg [1:0]  phase;
    reg [6:0]  pre_cnt;        // preamble + SFD chip counter
    reg [5:0]  ser_cnt;        // chip index inside current data chunk
    reg [7:0]  chunks_left;    // data chunks still to serialize
    reg        buf_sel;        // currently serialized buffer
    reg        fill_kick;
    reg        finishing;      // final chip has been consumed

    reg [2:0]  fill_state;
    localparam FILL_IDLE = 3'd0,
               FILL_BIT  = 3'd1,
               FILL_ROM  = 3'd2,
               FILL_CW   = 3'd3,
               FILL_DONE = 3'd4;
    reg [3:0]  fill_bit_cnt;   // global bits collected for current codeword
    reg        fill_second;    // collecting odd codeword of an interleaved pair
    reg [10:0] bit_addr;
    reg [5:0]  acc_i, acc_q;
    reg [31:0] cw_even_i, cw_even_q;
    reg        fill_done;      // ~buf_sel holds a complete chunk

    reg [63:0] buf_i [0:1];
    reg [63:0] buf_q [0:1];

    wire [10:0] frame_bits = PHR_BITS + {r_len, 3'b000};      // PHR + payload
    wire [4:0]  pad_bits   = r_rate ? (5'd24 - frame_bits % 5'd24)
                                    : (5'd6  - frame_bits % 5'd6);
    wire [10:0] total_bits = frame_bits + pad_bits;
    wire [8:0]  num_cw     = total_bits / (r_rate ? 9'd12 : 9'd6);
    wire [7:0]  total_chunks = r_rate ? {1'b0, num_cw[8:1]} : {1'b0, num_cw};
    wire [6:0]  pre_total  = (r_rate ? 7'd80 : 7'd32) + 7'd16;

    wire [5:0]  chunk_len_m1 = r_rate ? 6'd63 : 6'd3;
    wire [15:0] sfd_tab      = r_rate ? SFD_250K : SFD_1M;

    wire [3:0] bits_per_cw = r_rate ? 4'd12 : 4'd6;   // global bits per codeword

    function bit_ref;
        input [10:0] a;
        input [6:0]  len;
        begin
            if (a < PHR_BITS)
                bit_ref = (a < 7) ? len[a[2:0]] : 1'b0;
            else if (a < PHR_BITS + {len, 3'b000})
                bit_ref = ram[(a - PHR_BITS) >> 3][7 - ((a - PHR_BITS) & 3'b111)];
            else
                bit_ref = 1'b0;
        end
    endfunction

    wire bit_val  = bit_ref(bit_addr, r_len);
    wire bit_is_i = !bit_addr[0];         // even global index -> I path

    // codeword ROMs (registered read: address stable during FILL_ROM cycle)
    wire [31:0] cw_i_rom, cw_q_rom;
    wire [8:0] rom_addr_i = r_rate ? {3'b0, acc_i[5:0]} : {6'b0, acc_i[2:0]};
    wire [8:0] rom_addr_q = r_rate ? {3'b0, acc_q[5:0]} : {6'b0, acc_q[2:0]};

    // interleaver permutation: output chip j = combined[perm(j)],
    // combined = {odd codeword d (idx 32..63), even codeword c (idx 0..31)}
    function [5:0] perm;
        input [5:0] j;
        case (j)
            6'd0:  perm = 6'd0;  6'd1:  perm = 6'd1;  6'd2:  perm = 6'd2;  6'd3:  perm = 6'd3;
            6'd4:  perm = 6'd52; 6'd5:  perm = 6'd53; 6'd6:  perm = 6'd54; 6'd7:  perm = 6'd55;
            6'd8:  perm = 6'd8;  6'd9:  perm = 6'd9;  6'd10: perm = 6'd10; 6'd11: perm = 6'd11;
            6'd12: perm = 6'd60; 6'd13: perm = 6'd61; 6'd14: perm = 6'd62; 6'd15: perm = 6'd63;
            6'd16: perm = 6'd16; 6'd17: perm = 6'd17; 6'd18: perm = 6'd18; 6'd19: perm = 6'd19;
            6'd20: perm = 6'd36; 6'd21: perm = 6'd37; 6'd22: perm = 6'd38; 6'd23: perm = 6'd39;
            6'd24: perm = 6'd24; 6'd25: perm = 6'd25; 6'd26: perm = 6'd26; 6'd27: perm = 6'd27;
            6'd28: perm = 6'd44; 6'd29: perm = 6'd45; 6'd30: perm = 6'd46; 6'd31: perm = 6'd47;
            6'd32: perm = 6'd32; 6'd33: perm = 6'd33; 6'd34: perm = 6'd34; 6'd35: perm = 6'd35;
            6'd36: perm = 6'd20; 6'd37: perm = 6'd21; 6'd38: perm = 6'd22; 6'd39: perm = 6'd23;
            6'd40: perm = 6'd40; 6'd41: perm = 6'd41; 6'd42: perm = 6'd42; 6'd43: perm = 6'd43;
            6'd44: perm = 6'd28; 6'd45: perm = 6'd29; 6'd46: perm = 6'd30; 6'd47: perm = 6'd31;
            6'd48: perm = 6'd48; 6'd49: perm = 6'd49; 6'd50: perm = 6'd50; 6'd51: perm = 6'd51;
            6'd52: perm = 6'd4;  6'd53: perm = 6'd5;  6'd54: perm = 6'd6;  6'd55: perm = 6'd7;
            6'd56: perm = 6'd56; 6'd57: perm = 6'd57; 6'd58: perm = 6'd58; 6'd59: perm = 6'd59;
            6'd60: perm = 6'd12; 6'd61: perm = 6'd13; 6'd62: perm = 6'd14; default: perm = 6'd15;
        endcase
    endfunction

    wire [63:0] comb_i = {cw_i_rom, cw_even_i};   // [0..31]=even cw c0..c31, [32..63]=odd cw
    wire [63:0] comb_q = {cw_q_rom, cw_even_q};   // [0..31]=even cw c0..c31, [32..63]=odd cw

    integer jj;
    reg [63:0] perm_i, perm_q;
    always @* begin
        for (jj = 0; jj < 64; jj = jj + 1) begin
            perm_i[jj] = comb_i[perm(jj[5:0])];
            perm_q[jj] = comb_q[perm(jj[5:0])];
        end
    end

    // ------------------------------------------------------------------
    // payload RAM write port
    // ------------------------------------------------------------------
    assign payload_ready = !busy;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            wr_ptr <= 7'd0;
        else if (payload_valid && payload_ready) begin
            ram[wr_ptr] <= payload_data;
            wr_ptr      <= wr_ptr + 7'd1;
        end
    end

    // ------------------------------------------------------------------
    // main sequencing FSM
    // ------------------------------------------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st          <= ST_IDLE;
            busy        <= 1'b0;
            r_rate      <= 1'b0;
            r_len       <= 7'd0;
            phase       <= PH_PRE;
            pre_cnt     <= 7'd0;
            ser_cnt     <= 6'd0;
            chunks_left <= 8'd0;
            buf_sel     <= 1'b0;
            fill_kick   <= 1'b0;
            finishing   <= 1'b0;
        end else begin
            case (st)
                ST_IDLE: if (start) begin
                    r_rate <= data_rate;
                    r_len  <= payload_len;
                    st     <= ST_CFG;
                end
                ST_CFG: begin
                    phase       <= PH_PRE;
                    pre_cnt     <= 7'd0;
                    ser_cnt     <= 6'd0;
                    chunks_left <= total_chunks;
                    buf_sel     <= 1'b1;      // first refill goes to buffer 0
                    bit_addr    <= 11'd0;
                    fill_kick   <= 1'b1;
                    finishing   <= 1'b0;
                    busy        <= 1'b1;
                    st          <= ST_RUN;
                end
                ST_RUN: if (finishing) begin
                    busy <= 1'b0;
                    st   <= ST_IDLE;
                end
                default: st <= ST_IDLE;
            endcase
        end
    end

    // advance packet state on consumer latch pulses
    always @(posedge clk) begin
        if (st == ST_RUN && chip_latch) begin
            fill_kick <= 1'b0;
            case (phase)
                PH_PRE: begin
                    pre_cnt <= pre_cnt + 7'd1;
                    if (pre_cnt == pre_total - 7'd17)
                        phase <= PH_SFD;          // preamble done, SFD next
                    else if (pre_cnt == pre_total - 7'd1) begin
                        phase     <= PH_DATA;
                        buf_sel   <= ~buf_sel;
                        fill_kick <= 1'b1;
                    end
                end
                PH_SFD: begin
                    pre_cnt <= pre_cnt + 7'd1;
                    if (pre_cnt == pre_total - 7'd1) begin
                        phase     <= PH_DATA;
                        buf_sel   <= ~buf_sel;
                        fill_kick <= 1'b1;
                    end
                end
                PH_DATA: begin
                    if (ser_cnt == chunk_len_m1) begin
                        ser_cnt <= 6'd0;
                        if (chunks_left > 8'd1) begin
                            chunks_left <= chunks_left - 8'd1;
                            buf_sel     <= ~buf_sel;
                            fill_kick   <= 1'b1;
                        end else begin
                            finishing <= 1'b1;
                        end
                    end else begin
                        ser_cnt <= ser_cnt + 6'd1;
                    end
                end
                default: ;
            endcase
        end
    end

    // last chip overall: final data chunk, last position
    assign chip_last = busy && (phase == PH_DATA) &&
                       (ser_cnt == chunk_len_m1) && (chunks_left == 8'd1);

    // ------------------------------------------------------------------
    // chip bus mux
    // ------------------------------------------------------------------
    assign chip_valid = busy;
    assign chip_bus   = (phase == PH_PRE)  ? 2'b11 :
                        (phase == PH_SFD)  ? {sfd_tab[pre_cnt[3:0]],
                                              sfd_tab[pre_cnt[3:0]]} :
                                             {buf_i[buf_sel][ser_cnt],
                                              buf_q[buf_sel][ser_cnt]};

    // ------------------------------------------------------------------
    // chunk refill machine
    //
    // A chunk is the serialized group handed to the output mux:
    //   1 Mb/s  :  4 chips (one codeword)
    //   250 kb/s: 64 chips (two consecutive codewords, interleaved)
    // The machine refills the inactive buffer (~buf_sel); a refill always
    // finishes well before the next chunk swap (>= 38 chip-window cycles).
    // ------------------------------------------------------------------
    css_codeword_rom u_cwrom_i (.clk(clk), .rate(r_rate),
                                .addr(rom_addr_i), .cw(cw_i_rom));
    css_codeword_rom u_cwrom_q (.clk(clk), .rate(r_rate),
                                .addr(rom_addr_q), .cw(cw_q_rom));

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fill_state   <= FILL_IDLE;
            fill_bit_cnt <= 4'd0;
            fill_second  <= 1'b0;
            fill_done    <= 1'b0;
            bit_addr     <= 11'd0;
            acc_i        <= 6'd0;
            acc_q        <= 6'd0;
        end else begin
            case (fill_state)
                FILL_IDLE: begin
                    if (fill_kick) begin
                        fill_kick    <= 1'b0;
                        fill_state   <= FILL_BIT;
                        fill_bit_cnt <= 4'd0;
                        fill_second  <= 1'b0;
                        fill_done    <= 1'b0;
                    end
                end
                FILL_BIT: begin
                    if (bit_is_i)
                        acc_i <= {acc_i[4:0], bit_val};
                    else
                        acc_q <= {acc_q[4:0], bit_val};
                    bit_addr     <= bit_addr + 11'd1;
                    fill_bit_cnt <= fill_bit_cnt + 4'd1;
                    if (fill_bit_cnt == bits_per_cw - 4'd1)
                        fill_state <= FILL_ROM;
                end
                FILL_ROM: begin
                    // ROM output registered at the end of this cycle
                    fill_state <= FILL_CW;
                end
                FILL_CW: begin
                    if (!r_rate) begin
                        buf_i[~buf_sel] <= {{60{1'b0}}, cw_i_rom[3:0]};
                        buf_q[~buf_sel] <= {{60{1'b0}}, cw_q_rom[3:0]};
                        fill_state      <= FILL_DONE;
                    end else if (!fill_second) begin
                        cw_even_i    <= cw_i_rom;
                        cw_even_q    <= cw_q_rom;
                        fill_second  <= 1'b1;
                        fill_bit_cnt <= 4'd0;
                        fill_state   <= FILL_BIT;
                    end else begin
                        buf_i[~buf_sel] <= perm_i;
                        buf_q[~buf_sel] <= perm_q;
                        fill_state      <= FILL_DONE;
                    end
                end
                FILL_DONE: begin
                    fill_done  <= 1'b1;
                    fill_state <= FILL_IDLE;
                end
                default: fill_state <= FILL_IDLE;
            endcase
        end
    end

    // simulation guard: never swap into an unfinished buffer
    // synthesis translate_off
    always @(posedge clk) begin
        if (st == ST_RUN && chip_latch && (phase == PH_DATA) &&
            (ser_cnt == chunk_len_m1) && (chunks_left > 8'd1) && !fill_done)
            $display("FATAL: pkt_ctrl buffer underflow at %t", $time);
    end
    // synthesis translate_on

endmodule
