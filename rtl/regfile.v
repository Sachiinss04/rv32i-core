// 32x32 register file, x0 hardwired to zero, 2 async read ports, 1 sync write port
module regfile (
  input         clk,
  input         we,
  input  [4:0]  ra1,
  input  [4:0]  ra2,
  input  [4:0]  wa,
  input  [31:0] wd,
  output [31:0] rd1,
  output [31:0] rd2
);
  reg [31:0] regs [0:31];
  integer i;
  initial for (i = 0; i < 32; i = i + 1) regs[i] = 32'b0;

  assign rd1 = (ra1 == 5'd0) ? 32'b0 : regs[ra1];
  assign rd2 = (ra2 == 5'd0) ? 32'b0 : regs[ra2];

  always @(posedge clk)
    if (we && wa != 5'd0) regs[wa] <= wd;
endmodule
