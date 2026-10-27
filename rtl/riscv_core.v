// -----------------------------------------------------------------------
// riscv_core.v -- single-cycle RV32I core (Harvard: separate imem/dmem)
// Implements: LUI AUIPC JAL JALR BEQ BNE BLT BGE BLTU BGEU
//             LB LH LW LBU LHU SB SH SW, all OP-IMM and OP instructions.
// Not implemented: FENCE, ECALL/EBREAK (treated as NOP; testbench uses
// EBREAK as a stop marker), CSRs, misaligned accesses.
// -----------------------------------------------------------------------
module riscv_core (
  input         clk,
  input         rst,
  output [31:0] imem_addr,
  input  [31:0] imem_data,
  output [31:0] dmem_addr,
  output reg [31:0] dmem_wdata,
  output reg [3:0]  dmem_wstrb,
  output        dmem_we,
  input  [31:0] dmem_rdata
);
  reg  [31:0] pc;
  wire [31:0] inst = imem_data;
  assign imem_addr = pc;

  wire [6:0] opcode = inst[6:0];
  wire [2:0] f3     = inst[14:12];
  wire       f7b5   = inst[30];
  wire [4:0] rs1    = inst[19:15];
  wire [4:0] rs2    = inst[24:20];
  wire [4:0] rd     = inst[11:7];

  wire is_lui    = (opcode == 7'b0110111);
  wire is_auipc  = (opcode == 7'b0010111);
  wire is_jal    = (opcode == 7'b1101111);
  wire is_jalr   = (opcode == 7'b1100111);
  wire is_branch = (opcode == 7'b1100011);
  wire is_load   = (opcode == 7'b0000011);
  wire is_store  = (opcode == 7'b0100011);
  wire is_opimm  = (opcode == 7'b0010011);
  wire is_op     = (opcode == 7'b0110011);

  wire [31:0] imm_i = {{20{inst[31]}}, inst[31:20]};
  wire [31:0] imm_s = {{20{inst[31]}}, inst[31:25], inst[11:7]};
  wire [31:0] imm_b = {{19{inst[31]}}, inst[31], inst[7], inst[30:25], inst[11:8], 1'b0};
  wire [31:0] imm_u = {inst[31:12], 12'b0};
  wire [31:0] imm_j = {{11{inst[31]}}, inst[31], inst[19:12], inst[20], inst[30:21], 1'b0};

  // register file
  wire [31:0] rs1_v, rs2_v;
  reg  [31:0] wb;
  wire        rf_we = ~rst & (is_lui | is_auipc | is_jal | is_jalr |
                              is_load | is_opimm | is_op);
  regfile rf (.clk(clk), .we(rf_we), .ra1(rs1), .ra2(rs2),
              .wa(rd), .wd(wb), .rd1(rs1_v), .rd2(rs2_v));

  // ALU
  reg [3:0] alu_op;
  always @* begin
    alu_op = 4'd0;
    if (is_op | is_opimm) begin
      case (f3)
        3'b000: alu_op = (is_op & f7b5) ? 4'd1 : 4'd0;
        3'b001: alu_op = 4'd2;
        3'b010: alu_op = 4'd3;
        3'b011: alu_op = 4'd4;
        3'b100: alu_op = 4'd5;
        3'b101: alu_op = f7b5 ? 4'd7 : 4'd6;
        3'b110: alu_op = 4'd8;
        3'b111: alu_op = 4'd9;
      endcase
    end
  end

  wire [31:0] alu_b = is_op ? rs2_v : (is_store ? imm_s : imm_i);
  wire [31:0] alu_y;
  alu u_alu (.a(rs1_v), .b(alu_b), .op(alu_op), .y(alu_y));

  // branch compare
  reg take;
  always @* begin
    case (f3)
      3'b000:  take = (rs1_v == rs2_v);
      3'b001:  take = (rs1_v != rs2_v);
      3'b100:  take = ($signed(rs1_v) <  $signed(rs2_v));
      3'b101:  take = ($signed(rs1_v) >= $signed(rs2_v));
      3'b110:  take = (rs1_v <  rs2_v);
      3'b111:  take = (rs1_v >= rs2_v);
      default: take = 1'b0;
    endcase
  end

  // next PC
  wire [31:0] pc4      = pc + 32'd4;
  wire [31:0] pc_br    = pc + imm_b;
  wire [31:0] pc_jal   = pc + imm_j;
  wire [31:0] pc_jalr  = (rs1_v + imm_i) & ~32'd1;
  wire [31:0] next_pc  = is_jal  ? pc_jal  :
                         is_jalr ? pc_jalr :
                         (is_branch & take) ? pc_br : pc4;

  always @(posedge clk) begin
    if (rst) pc <= 32'b0;
    else     pc <= next_pc;
  end

  // data memory interface
  assign dmem_addr = alu_y;           // rs1 + imm for loads/stores
  assign dmem_we   = ~rst & is_store;
  wire [1:0] off   = dmem_addr[1:0];

  wire [31:0] rsh = dmem_rdata >> {off, 3'b000};
  reg  [31:0] load_v;
  always @* begin
    case (f3)
      3'b000:  load_v = {{24{rsh[7]}},  rsh[7:0]};   // LB
      3'b001:  load_v = {{16{rsh[15]}}, rsh[15:0]};  // LH
      3'b010:  load_v = dmem_rdata;                  // LW
      3'b100:  load_v = {24'b0, rsh[7:0]};           // LBU
      3'b101:  load_v = {16'b0, rsh[15:0]};          // LHU
      default: load_v = 32'b0;
    endcase
  end

  always @* begin
    case (f3[1:0])
      2'b00: begin dmem_wdata = {4{rs2_v[7:0]}};   dmem_wstrb = 4'b0001 << off; end // SB
      2'b01: begin dmem_wdata = {2{rs2_v[15:0]}};  dmem_wstrb = off[1] ? 4'b1100 : 4'b0011; end // SH
      default: begin dmem_wdata = rs2_v;           dmem_wstrb = 4'b1111; end        // SW
    endcase
  end

  // write-back
  always @* begin
    if      (is_lui)             wb = imm_u;
    else if (is_auipc)           wb = pc + imm_u;
    else if (is_jal | is_jalr)   wb = pc4;
    else if (is_load)            wb = load_v;
    else                         wb = alu_y;
  end
endmodule
