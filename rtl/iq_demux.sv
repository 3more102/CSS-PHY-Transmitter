module iq_demux (
  input  logic pair_valid,
  input  logic first_bit,
  input  logic second_bit,
  output logic i_valid,
  output logic q_valid,
  output logic i_bit,
  output logic q_bit
);
  // The supplied MATLAB stream is consumed as consecutive bit pairs:
  // first serial bit -> I, second serial bit -> Q.  The controller already
  // fetches those two consecutive bits together, so this module makes that
  // mandatory DEMUX boundary explicit without changing stream ordering.
  always_comb begin
    i_valid = pair_valid;
    q_valid = pair_valid;
    i_bit = first_bit;
    q_bit = second_bit;
  end
endmodule
