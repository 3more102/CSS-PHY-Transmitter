module bit_interleaver (
  input  logic [63:0] in_bits,
  output logic [63:0] out_bits
);
  // in_bits[63] is input bit 0; out_bits[63] is output bit 0.
  always_comb begin
    out_bits = 64'b0;
    out_bits[63] = in_bits[63];
    out_bits[62] = in_bits[62];
    out_bits[61] = in_bits[61];
    out_bits[60] = in_bits[60];
    out_bits[59] = in_bits[11];
    out_bits[58] = in_bits[10];
    out_bits[57] = in_bits[9];
    out_bits[56] = in_bits[8];
    out_bits[55] = in_bits[55];
    out_bits[54] = in_bits[54];
    out_bits[53] = in_bits[53];
    out_bits[52] = in_bits[52];
    out_bits[51] = in_bits[3];
    out_bits[50] = in_bits[2];
    out_bits[49] = in_bits[1];
    out_bits[48] = in_bits[0];
    out_bits[47] = in_bits[47];
    out_bits[46] = in_bits[46];
    out_bits[45] = in_bits[45];
    out_bits[44] = in_bits[44];
    out_bits[43] = in_bits[27];
    out_bits[42] = in_bits[26];
    out_bits[41] = in_bits[25];
    out_bits[40] = in_bits[24];
    out_bits[39] = in_bits[39];
    out_bits[38] = in_bits[38];
    out_bits[37] = in_bits[37];
    out_bits[36] = in_bits[36];
    out_bits[35] = in_bits[19];
    out_bits[34] = in_bits[18];
    out_bits[33] = in_bits[17];
    out_bits[32] = in_bits[16];
    out_bits[31] = in_bits[31];
    out_bits[30] = in_bits[30];
    out_bits[29] = in_bits[29];
    out_bits[28] = in_bits[28];
    out_bits[27] = in_bits[43];
    out_bits[26] = in_bits[42];
    out_bits[25] = in_bits[41];
    out_bits[24] = in_bits[40];
    out_bits[23] = in_bits[23];
    out_bits[22] = in_bits[22];
    out_bits[21] = in_bits[21];
    out_bits[20] = in_bits[20];
    out_bits[19] = in_bits[35];
    out_bits[18] = in_bits[34];
    out_bits[17] = in_bits[33];
    out_bits[16] = in_bits[32];
    out_bits[15] = in_bits[15];
    out_bits[14] = in_bits[14];
    out_bits[13] = in_bits[13];
    out_bits[12] = in_bits[12];
    out_bits[11] = in_bits[59];
    out_bits[10] = in_bits[58];
    out_bits[9] = in_bits[57];
    out_bits[8] = in_bits[56];
    out_bits[7] = in_bits[7];
    out_bits[6] = in_bits[6];
    out_bits[5] = in_bits[5];
    out_bits[4] = in_bits[4];
    out_bits[3] = in_bits[51];
    out_bits[2] = in_bits[50];
    out_bits[1] = in_bits[49];
    out_bits[0] = in_bits[48];
  end
endmodule
