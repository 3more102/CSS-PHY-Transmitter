module css_tx_controller (
  input  logic       clk,
  input  logic       reset,
  input  logic       start,
  input  logic       rate,
  input  logic [7:0] payload_length,
  output logic [6:0] payload_rd_addr,
  input  logic [7:0] payload_rd_data,
  output logic       chip_valid,
  input  logic       chip_ready,
  output logic       chip_i,
  output logic       chip_q,
  output logic       source_done,
  output logic       busy
);
  typedef enum logic [3:0] {
    ST_IDLE,
    ST_SYNC,
    ST_COLLECT_A,
    ST_LATCH_A,
    ST_COLLECT_B,
    ST_LATCH_B,
    ST_EMIT_1M,
    ST_EMIT_250
  } state_t;

  state_t state;
  logic [7:0] payload_length_r;
  logic [6:0] sync_index;
  logic [10:0] pair_index;
  logic [2:0] collect_count;
  logic [4:0] i_shift, q_shift;
  logic [5:0] symbol_i, symbol_q;
  logic [3:0] cw_i_1m, cw_q_1m;
  logic [31:0] cw_i_250, cw_q_250;
  logic [31:0] cw_i_a, cw_q_a;
  logic [63:0] inter_i_in, inter_q_in;
  logic [63:0] inter_i_out, inter_q_out;
  logic [6:0] emit_index;

  logic [11:0] phr;
  logic [10:0] total_bits;
  logic [10:0] total_pairs;
  logic sync_chip, sync_valid;
  logic pair_first_raw, pair_second_raw;
  logic pair_i, pair_q;
  logic demux_i_valid, demux_q_valid;

  logic [8:0] pair_payload_index;
  logic [2:0] bit_select;
  logic [6:0] sync_last;
  logic [10:0] payload_pair_end;
  /* verilator lint_off UNUSEDSIGNAL */
  logic [5:0] pad_bits_unused;
  /* verilator lint_on UNUSEDSIGNAL */

  phr_generator u_phr (.payload_length(payload_length_r), .phr_bits(phr));
  zero_pad_framer u_pad (
    .rate(rate), .payload_length(payload_length_r),
    .pad_bits(pad_bits_unused), .total_bits(total_bits)
  );
  preamble_sfd_rom u_sync_rom (.rate(rate), .index(sync_index), .chip(sync_chip), .valid(sync_valid));

  iq_demux u_demux (
    .pair_valid((state == ST_COLLECT_A) || (state == ST_COLLECT_B)),
    .first_bit(pair_first_raw), .second_bit(pair_second_raw),
    .i_valid(demux_i_valid), .q_valid(demux_q_valid),
    .i_bit(pair_i), .q_bit(pair_q)
  );

  symbol_mapper_1m u_map_i_1m (.symbol(symbol_i[2:0]), .codeword(cw_i_1m));
  symbol_mapper_1m u_map_q_1m (.symbol(symbol_q[2:0]), .codeword(cw_q_1m));
  symbol_mapper_250k u_map_i_250 (.symbol(symbol_i), .codeword(cw_i_250));
  symbol_mapper_250k u_map_q_250 (.symbol(symbol_q), .codeword(cw_q_250));

  assign inter_i_in = {cw_i_a, cw_i_250};
  assign inter_q_in = {cw_q_a, cw_q_250};
  bit_interleaver u_inter_i (.in_bits(inter_i_in), .out_bits(inter_i_out));
  bit_interleaver u_inter_q (.in_bits(inter_q_in), .out_bits(inter_q_out));

  always_comb begin
    total_pairs = total_bits >> 1;
    sync_last = rate ? 7'd95 : 7'd47;
    payload_pair_end = 11'd6 + ({3'd0, payload_length_r} << 2);
    pair_payload_index = 9'd0;
    bit_select = 3'd0;
    payload_rd_addr = 7'd0;
    if ((pair_index >= 11'd6) && (pair_index < payload_pair_end)) begin
      pair_payload_index = 9'(pair_index - 11'd6);
      payload_rd_addr = pair_payload_index[8:2];
      bit_select = {pair_payload_index[1:0], 1'b0};
    end
  end

  always_comb begin
    pair_first_raw = 1'b0;
    pair_second_raw = 1'b0;
    if (pair_index < 11'd6) begin
      pair_first_raw = phr[pair_index * 2];
      pair_second_raw = phr[pair_index * 2 + 1];
    end else if (pair_index < payload_pair_end) begin
      pair_first_raw = payload_rd_data[bit_select];
      pair_second_raw = payload_rd_data[bit_select + 3'd1];
    end
  end

  always_comb begin
    chip_valid = 1'b0;
    chip_i = 1'b0;
    chip_q = 1'b0;
    busy = (state != ST_IDLE);

    case (state)
      ST_SYNC: begin
        chip_valid = sync_valid;
        chip_i = sync_chip;
        chip_q = sync_chip;
      end
      ST_EMIT_1M: begin
        chip_valid = 1'b1;
        chip_i = cw_i_1m[3-emit_index];
        chip_q = cw_q_1m[3-emit_index];
      end
      ST_EMIT_250: begin
        chip_valid = 1'b1;
        chip_i = inter_i_out[63-emit_index];
        chip_q = inter_q_out[63-emit_index];
      end
      default: chip_valid = 1'b0;
    endcase
  end

  always_ff @(posedge clk) begin
    if (reset) begin
      state <= ST_IDLE;
      payload_length_r <= 8'd0;
      sync_index <= 7'd0;
      pair_index <= 11'd0;
      collect_count <= 3'd0;
      i_shift <= 5'd0;
      q_shift <= 5'd0;
      symbol_i <= 6'd0;
      symbol_q <= 6'd0;
      cw_i_a <= 32'd0;
      cw_q_a <= 32'd0;
      emit_index <= 7'd0;
      source_done <= 1'b0;
    end else begin
      source_done <= 1'b0;
      case (state)
        ST_IDLE: begin
          if (start && payload_length <= css_phy_pkg::MAX_PAYLOAD_BYTES) begin
            payload_length_r <= payload_length;
            sync_index <= 7'd0;
            pair_index <= 11'd0;
            collect_count <= 3'd0;
            i_shift <= 5'd0;
            q_shift <= 5'd0;
            emit_index <= 7'd0;
            state <= ST_SYNC;
          end
        end
        ST_SYNC: begin
          if (chip_valid && chip_ready) begin
            if (sync_index == sync_last) begin
              collect_count <= 3'd0;
              i_shift <= 5'd0;
              q_shift <= 5'd0;
              state <= ST_COLLECT_A;
            end else sync_index <= sync_index + 7'd1;
          end
        end
        ST_COLLECT_A: begin
          if (demux_i_valid && demux_q_valid) begin
            i_shift <= {i_shift[3:0], pair_i};
            q_shift <= {q_shift[3:0], pair_q};
            pair_index <= pair_index + 11'd1;
            if ((!rate && collect_count == 3'd2) || (rate && collect_count == 3'd5)) begin
              if (rate) begin
                symbol_i <= {i_shift[4:0], pair_i};
                symbol_q <= {q_shift[4:0], pair_q};
              end else begin
                symbol_i <= {3'd0, i_shift[1:0], pair_i};
                symbol_q <= {3'd0, q_shift[1:0], pair_q};
              end
              collect_count <= 3'd0;
              i_shift <= 5'd0;
              q_shift <= 5'd0;
              state <= ST_LATCH_A;
            end else collect_count <= collect_count + 3'd1;
          end
        end
        ST_LATCH_A: begin
          if (rate) begin
            cw_i_a <= cw_i_250;
            cw_q_a <= cw_q_250;
            collect_count <= 3'd0;
            state <= ST_COLLECT_B;
          end else begin
            emit_index <= 7'd0;
            state <= ST_EMIT_1M;
          end
        end
        ST_COLLECT_B: begin
          if (demux_i_valid && demux_q_valid) begin
            i_shift <= {i_shift[3:0], pair_i};
            q_shift <= {q_shift[3:0], pair_q};
            pair_index <= pair_index + 11'd1;
            if (collect_count == 3'd5) begin
              symbol_i <= {i_shift[4:0], pair_i};
              symbol_q <= {q_shift[4:0], pair_q};
              collect_count <= 3'd0;
              i_shift <= 5'd0;
              q_shift <= 5'd0;
              state <= ST_LATCH_B;
            end else collect_count <= collect_count + 3'd1;
          end
        end
        ST_LATCH_B: begin
          emit_index <= 7'd0;
          state <= ST_EMIT_250;
        end
        ST_EMIT_1M: begin
          if (chip_valid && chip_ready) begin
            if (emit_index == 7'd3) begin
              emit_index <= 7'd0;
              if (pair_index >= total_pairs) begin
                source_done <= 1'b1;
                state <= ST_IDLE;
              end else state <= ST_COLLECT_A;
            end else emit_index <= emit_index + 7'd1;
          end
        end
        ST_EMIT_250: begin
          if (chip_valid && chip_ready) begin
            if (emit_index == 7'd63) begin
              emit_index <= 7'd0;
              if (pair_index >= total_pairs) begin
                source_done <= 1'b1;
                state <= ST_IDLE;
              end else state <= ST_COLLECT_A;
            end else emit_index <= emit_index + 7'd1;
          end
        end
        default: state <= ST_IDLE;
      endcase
    end
  end
endmodule
