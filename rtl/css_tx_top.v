// css_tx_top.v - IEEE 802.15.4 CSS PHY transmitter, top level
//
// Complex baseband sample output (6-bit DAC model rotated by DQPSK, 7-bit
// signed result), one sample per clock while o_valid is asserted.
module css_tx_top (
    input  wire       clk,
    input  wire       rst_n,
    // packet configuration
    input  wire       start,          // one-cycle pulse
    input  wire       data_rate,      // 0 = 1 Mb/s, 1 = 250 kb/s
    input  wire [1:0] chirp_index,    // 0..3 => chirp sequence m = 1..4
    input  wire [6:0] payload_len,    // payload bytes, 1..127
    // payload byte stream (preloaded before start)
    output wire       payload_ready,
    input  wire       payload_valid,
    input  wire [7:0] payload_data,
    // complex modulated output
    output wire signed [6:0] o_i,
    output wire signed [6:0] o_q,
    output wire              o_valid,
    output wire              o_sop,
    output wire              o_eop
);

    wire        busy;
    wire [1:0]  chip_bus;
    wire        chip_valid;
    wire        chip_last;
    wire        chip_advance;

    css_pkt_ctrl #(.PAYLOAD_MAX(127)) u_ctrl (
        .clk           (clk),
        .rst_n         (rst_n),
        .start         (start),
        .data_rate     (data_rate),
        .payload_len   (payload_len),
        .payload_ready (payload_ready),
        .payload_valid (payload_valid),
        .payload_data  (payload_data),
        .chip_latch    (chip_advance),
        .busy          (busy),
        .chip_valid    (chip_valid),
        .chip_bus      (chip_bus),
        .chip_last     (chip_last)
    );

    css_dqcsk_mod u_mod (
        .clk        (clk),
        .rst_n      (rst_n),
        .chirp_index(chirp_index),
        .busy       (busy),
        .chip_bus   (chip_bus),
        .chip_last  (chip_last),
        .chip_advance (chip_advance),
        .o_i        (o_i),
        .o_q        (o_q),
        .o_valid    (o_valid),
        .o_sop      (o_sop),
        .o_eop      (o_eop)
    );

endmodule
