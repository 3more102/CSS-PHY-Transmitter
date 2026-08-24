// css_codeword_rom.v - bi-orthogonal codeword tables (IEEE 802.15.4 Table 26a/b)
//
// rate 0 (1 Mb/s):   8 codewords  x  4 chips
// rate 1 (250 kb/s): 512 codewords x 32 chips
// Chip bit value: 1 => +1, 0 => -1. c0 is the LSB of each entry.
module css_codeword_rom (
    input  wire        clk,
    input  wire        rate,     // 0 = 1 Mb/s, 1 = 250 kb/s
    input  wire [8:0]  addr,
    output reg  [31:0] cw
);
    reg [3:0]  m4  [0:7];
    reg [31:0] m32 [0:511];

    // synthesis translate_off
    // Missing-file detector shadow word (sim-only): m32 itself is
    // pre-zero-filled (entries 64..511 are unreachable and legitimately
    // stay 0), so an absent cw32.hex leaves no X residue there and the
    // old guard could never fire.  This shadow starts fully X.
    reg [31:0] rom_present [0:0];
    initial begin
        rom_present[0] = 32'hxxxxxxxx;
        $readmemh("cw32.hex", rom_present);
        if (^rom_present[0] === 1'bx)
            $display("FATAL: cw32.hex missing/unreadable - codeword ROM unloaded");
    end
    // synthesis translate_on

    integer i;
    initial begin
        // hadamard(4) followed by its negation, identical to codeword_1Mbs.txt.
        // Stored with c0 at bit 0: the serializer emits bit 0 first and the
        // reference model sends c0 first (ChirpSpreadSpectrum_Tx.m P/S).
        m4[0] = 4'b1111; m4[1] = 4'b0101; m4[2] = 4'b0011; m4[3] = 4'b1001;
        m4[4] = 4'b0000; m4[5] = 4'b1010; m4[6] = 4'b1100; m4[7] = 4'b0110;
        for (i = 0; i < 512; i = i + 1)
            m32[i] = 32'h0;
        $readmemh("cw32.hex", m32);
        // cw32.hex stores c0 at the MSB (text order); re-map so c0 = bit 0
        for (i = 0; i < 512; i = i + 1) begin : rev
            integer b;
            reg [31:0] tmp;
            begin
                tmp = m32[i];
                for (b = 0; b < 32; b = b + 1)
                    m32[i][b] = tmp[31 - b];
            end
        end
    end

    always @(posedge clk) begin
        if (rate)
            cw <= m32[addr];
        else
            cw <= {28'h0, m4[addr[2:0]]};
    end
endmodule
