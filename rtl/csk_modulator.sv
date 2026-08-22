module csk_modulator (
  input  logic clk,
  input  logic reset,
  input  logic sample_ce,
  input  logic group_valid,
  output logic group_ready,
  input  logic [2:0] chirp_index,
  input  logic group_odd,
  input  logic signed [2:0] s0_real, input logic signed [2:0] s0_imag,
  input  logic signed [2:0] s1_real, input logic signed [2:0] s1_imag,
  input  logic signed [2:0] s2_real, input logic signed [2:0] s2_imag,
  input  logic signed [2:0] s3_real, input logic signed [2:0] s3_imag,
  output logic busy,
  output logic sample_valid,
  output logic signed [7:0] sample_real,
  output logic signed [7:0] sample_imag,
  output logic group_done
);
  logic active;
  logic pending_valid;
  logic [8:0] sample_index;
  logic [7:0] rom_addr;
  logic signed [5:0] chirp_real, chirp_imag;

  logic signed [2:0] r0,i0,r1,i1,r2,i2,r3,i3;
  logic signed [2:0] pr0,pi0,pr1,pi1,pr2,pi2,pr3,pi3;
  logic signed [2:0] sel_real, sel_imag;
  logic [2:0] stored_index, pending_index;
  logic stored_odd, pending_odd;
  logic [6:0] gap_len;
  logic [8:0] last_index;
  logic at_final;
  logic finishing;
  logic enqueue;

  logic signed [8:0] mult_rr, mult_ii, mult_ri, mult_ir;
  logic signed [7:0] calc_real_8, calc_imag_8;

  chirp_rom u_chirp_rom (
    .chirp_index(stored_index), .addr(rom_addr),
    .chirp_real(chirp_real), .chirp_imag(chirp_imag)
  );

  assign busy = active;
  assign at_final = active && (sample_index == last_index);
  assign finishing = at_final && sample_ce;
  assign group_ready = !active || !pending_valid || finishing;
  assign enqueue = group_valid && group_ready;

  always_comb begin
    unique case (stored_index)
      3'd1: gap_len = stored_odd ? 7'd70 : 7'd10;
      3'd2: gap_len = stored_odd ? 7'd60 : 7'd20;
      3'd3: gap_len = stored_odd ? 7'd50 : 7'd30;
      3'd4: gap_len = 7'd40;
      default: gap_len = 7'd40;
    endcase
    last_index = (css_phy_pkg::ACTIVE_CHIRP_SAMPLES - 9'd1) + {2'd0, gap_len};
    rom_addr = sample_index[7:0];

    if (sample_index < css_phy_pkg::TSUB_SAMPLES) begin sel_real=r0; sel_imag=i0; end
    else if (sample_index < (css_phy_pkg::TSUB_SAMPLES << 1)) begin sel_real=r1; sel_imag=i1; end
    else if (sample_index < (css_phy_pkg::TSUB_SAMPLES + (css_phy_pkg::TSUB_SAMPLES << 1))) begin sel_real=r2; sel_imag=i2; end
    else begin sel_real=r3; sel_imag=i3; end

    mult_rr = $signed(chirp_real) * $signed(sel_real);
    mult_ii = $signed(chirp_imag) * $signed(sel_imag);
    mult_ri = $signed(chirp_real) * $signed(sel_imag);
    mult_ir = $signed(chirp_imag) * $signed(sel_real);
    calc_real_8 = 8'($signed(mult_rr) - $signed(mult_ii));
    calc_imag_8 = 8'($signed(mult_ri) + $signed(mult_ir));
  end

  task automatic load_current_from_input;
    begin
      r0<=s0_real; i0<=s0_imag; r1<=s1_real; i1<=s1_imag;
      r2<=s2_real; i2<=s2_imag; r3<=s3_real; i3<=s3_imag;
      stored_odd <= group_odd;
      stored_index <= chirp_index;
    end
  endtask

  task automatic load_pending_from_input;
    begin
      pr0<=s0_real; pi0<=s0_imag; pr1<=s1_real; pi1<=s1_imag;
      pr2<=s2_real; pi2<=s2_imag; pr3<=s3_real; pi3<=s3_imag;
      pending_odd <= group_odd;
      pending_index <= chirp_index;
    end
  endtask

  task automatic promote_pending;
    begin
      r0<=pr0; i0<=pi0; r1<=pr1; i1<=pi1;
      r2<=pr2; i2<=pi2; r3<=pr3; i3<=pi3;
      stored_odd <= pending_odd;
      stored_index <= pending_index;
    end
  endtask

  always_ff @(posedge clk) begin
    if (reset) begin
      active <= 1'b0;
      pending_valid <= 1'b0;
      sample_valid <= 1'b0;
      sample_real <= 8'sd0;
      sample_imag <= 8'sd0;
      group_done <= 1'b0;
      sample_index <= 9'd0;
      stored_odd <= 1'b0;
      pending_odd <= 1'b0;
      stored_index <= 3'd1;
      pending_index <= 3'd1;
      r0<=0; i0<=0; r1<=0; i1<=0; r2<=0; i2<=0; r3<=0; i3<=0;
      pr0<=0; pi0<=0; pr1<=0; pi1<=0; pr2<=0; pi2<=0; pr3<=0; pi3<=0;
    end else begin
      sample_valid <= 1'b0;
      group_done <= 1'b0;

      if (!active) begin
        if (enqueue) begin
          load_current_from_input();
          active <= 1'b1;
          pending_valid <= 1'b0;
          sample_index <= 9'd0;
        end
      end else begin
        if (sample_ce) begin
          sample_valid <= 1'b1;
          if (sample_index < css_phy_pkg::ACTIVE_CHIRP_SAMPLES) begin
            sample_real <= calc_real_8;
            sample_imag <= calc_imag_8;
          end else begin
            sample_real <= 8'sd0;
            sample_imag <= 8'sd0;
          end

          if (at_final) begin
            group_done <= 1'b1;
            sample_index <= 9'd0;
            if (pending_valid) begin
              promote_pending();
              active <= 1'b1;
              if (enqueue) begin
                load_pending_from_input();
                pending_valid <= 1'b1;
              end else begin
                pending_valid <= 1'b0;
              end
            end else if (enqueue) begin
              load_current_from_input();
              active <= 1'b1;
              pending_valid <= 1'b0;
            end else begin
              active <= 1'b0;
              pending_valid <= 1'b0;
            end
          end else begin
            sample_index <= sample_index + 9'd1;
            if (enqueue) begin
              load_pending_from_input();
              pending_valid <= 1'b1;
            end
          end
        end else if (enqueue) begin
          load_pending_from_input();
          pending_valid <= 1'b1;
        end
      end
    end
  end
endmodule
