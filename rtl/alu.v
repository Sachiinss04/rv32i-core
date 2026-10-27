// 32-bit ALU for RV32I
module alu (
  input  [31:0] a,
  input  [31:0] b,
  input  [3:0]  op,
  output reg [31:0] y
);
  always @* begin
    case (op)
      4'd0:    y = a + b;                               // ADD
      4'd1:    y = a - b;                               // SUB
      4'd2:    y = a << b[4:0];                         // SLL
      4'd3:    y = {31'b0, ($signed(a) < $signed(b))};  // SLT
      4'd4:    y = {31'b0, (a < b)};                    // SLTU
      4'd5:    y = a ^ b;                               // XOR
      4'd6:    y = a >> b[4:0];                         // SRL
      4'd7:    y = $signed(a) >>> b[4:0];               // SRA
      4'd8:    y = a | b;                               // OR
      4'd9:    y = a & b;                               // AND
      default: y = 32'b0;
    endcase
  end
endmodule
