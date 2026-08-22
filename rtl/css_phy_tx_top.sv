module css_phy_tx_top #(
  parameter integer DATA_RATE = 0,
  parameter integer CHIRP_INDEX = 1,
  parameter integer SAMPLE_DIV = 1
) (
  input  logic       clk,
  input  logic       reset,
  input  logic       start_Tx,
  input  logic [7:0] payloadLength,
  input  logic       payload_wr_en,
  input  logic [6:0] payload_addr,
  input  logic [7:0] payload_din,
  output logic       done_Tx,
  output logic signed [7:0] Tx_real,
  output logic signed [7:0] Tx_imag
);
  localparam logic RATE_SEL = (DATA_RATE != 0);
  localparam logic [2:0] CHIRP_SEL = CHIRP_INDEX[2:0];
  localparam integer SAMPLE_DIV_W = (SAMPLE_DIV <= 1) ? 1 : $clog2(SAMPLE_DIV);
  localparam logic [SAMPLE_DIV_W-1:0] SAMPLE_DIV_LAST = SAMPLE_DIV - 1;

  logic [6:0] payload_rd_addr;
  logic [7:0] payload_rd_data;
  logic source_chip_valid, source_chip_ready;
  logic source_chip_i, source_chip_q;
  logic source_done, controller_busy;
  logic controller_start;
  logic signed [2:0] qpsk_real, qpsk_imag;
  logic dq_valid;
  logic signed [2:0] dq_real, dq_imag;
  logic tx_active;
  logic source_done_seen;
  logic [1:0] group_count;
  logic group_full;
  logic group_odd;
  logic next_group_odd;
  logic signed [2:0] g0r,g0i,g1r,g1i,g2r,g2i,g3r,g3i;
  logic csk_group_ready;
  logic sample_ce;
  logic [SAMPLE_DIV_W-1:0] sample_div_count;
  logic csk_busy;
  logic csk_group_done;
  logic sample_valid_int;
  logic signed [7:0] sample_real_int, sample_imag_int;

`ifndef SYNTHESIS
  initial begin
    if (DATA_RATE != 0 && DATA_RATE != 1) $error("DATA_RATE must be 0 (1 Mbps) or 1 (250 kbps)");
    if (CHIRP_INDEX < 1 || CHIRP_INDEX > 4) $error("CHIRP_INDEX must be 1..4");
    if (SAMPLE_DIV < 1) $error("SAMPLE_DIV must be >= 1");
  end
`endif

  payload_ram u_payload_ram (
    .clk(clk), .wr_en(payload_wr_en), .wr_addr(payload_addr), .wr_data(payload_din),
    .rd_addr(payload_rd_addr), .rd_data(payload_rd_data)
  );

  assign controller_start = start_Tx && !tx_active && (payloadLength <= 8'd127);

  css_tx_controller u_controller (
    .clk(clk), .reset(reset), .start(controller_start), .rate(RATE_SEL),
    .payload_length(payloadLength),
    .payload_rd_addr(payload_rd_addr), .payload_rd_data(payload_rd_data),
    .chip_valid(source_chip_valid), .chip_ready(source_chip_ready),
    .chip_i(source_chip_i), .chip_q(source_chip_q),
    .source_done(source_done), .busy(controller_busy)
  );

  qpsk_mapper u_qpsk (
    .chip_i(source_chip_i), .chip_q(source_chip_q),
    .qpsk_real(qpsk_real), .qpsk_imag(qpsk_imag)
  );

  assign source_chip_ready = tx_active && !group_full;

  dqpsk_encoder u_dqpsk (
    .clk(clk), .reset(reset), .init_packet(controller_start),
    .in_valid(source_chip_valid), .accept(source_chip_ready),
    .in_real(qpsk_real), .in_imag(qpsk_imag),
    .out_valid(dq_valid), .out_real(dq_real), .out_imag(dq_imag)
  );

  csk_modulator u_csk (
    .clk(clk), .reset(reset), .sample_ce(sample_ce),
    .group_valid(group_full), .group_ready(csk_group_ready),
    .chirp_index(CHIRP_SEL), .group_odd(group_odd),
    .s0_real(g0r), .s0_imag(g0i), .s1_real(g1r), .s1_imag(g1i),
    .s2_real(g2r), .s2_imag(g2i), .s3_real(g3r), .s3_imag(g3i),
    .busy(csk_busy), .sample_valid(sample_valid_int),
    .sample_real(sample_real_int), .sample_imag(sample_imag_int),
    .group_done(csk_group_done)
  );

  assign Tx_real = sample_real_int;
  assign Tx_imag = sample_imag_int;

  generate
    if (SAMPLE_DIV == 1) begin : g_sample_ce_one
      always_comb sample_ce = 1'b1;
      always_ff @(posedge clk) sample_div_count <= '0;
    end else begin : g_sample_ce_div
      always_comb sample_ce = (sample_div_count == SAMPLE_DIV_LAST);
      always_ff @(posedge clk) begin
        if (reset || sample_ce) sample_div_count <= '0;
        else sample_div_count <= sample_div_count + 1'b1;
      end
    end
  endgenerate

  always_ff @(posedge clk) begin
    if (reset) begin
      tx_active <= 1'b0;
      source_done_seen <= 1'b0;
      done_Tx <= 1'b0;
      group_count <= 2'd0;
      group_full <= 1'b0;
      group_odd <= 1'b0;
      next_group_odd <= 1'b0;
      g0r<=0; g0i<=0; g1r<=0; g1i<=0; g2r<=0; g2i<=0; g3r<=0; g3i<=0;
    end else begin
      done_Tx <= 1'b0;
      if (controller_start) begin
        tx_active <= 1'b1;
        source_done_seen <= 1'b0;
        group_count <= 2'd0;
        group_full <= 1'b0;
        group_odd <= 1'b0;
        next_group_odd <= 1'b0;
      end else begin
        if (source_done) source_done_seen <= 1'b1;
        if (group_full && csk_group_ready) group_full <= 1'b0;
        if (dq_valid) begin
          unique case (group_count)
            2'd0: begin g0r<=dq_real; g0i<=dq_imag; group_count<=2'd1; end
            2'd1: begin g1r<=dq_real; g1i<=dq_imag; group_count<=2'd2; end
            2'd2: begin g2r<=dq_real; g2i<=dq_imag; group_count<=2'd3; end
            2'd3: begin
              g3r<=dq_real; g3i<=dq_imag;
              group_count <= 2'd0;
              group_full <= 1'b1;
              group_odd <= next_group_odd;
              next_group_odd <= ~next_group_odd;
            end
          endcase
        end
        if (tx_active && source_done_seen && !controller_busy && !csk_busy && !group_full && group_count == 2'd0) begin
          done_Tx <= 1'b1;
          tx_active <= 1'b0;
        end
      end
    end
  end
endmodule
