// -----------------------------------------------------------------------
// tb_core.v -- loads a hex program (+HEX=file), runs until EBREAK
// (0x00100073) is fetched, then dumps 32 registers + 512 data words to
// +OUT=file. tools/run_tests.py compares that dump to the Python ISS.
// -----------------------------------------------------------------------
`timescale 1ns/1ps
module tb_core;
  reg clk = 0;
  reg rst = 1;
  always #5 clk = ~clk;

  reg [31:0] imem [0:1023];   // 4 KB instruction memory
  reg [7:0]  dmem [0:4095];   // 4 KB data memory

  wire [31:0] imem_addr, dmem_addr, dmem_wdata, dmem_rdata;
  wire [3:0]  dmem_wstrb;
  wire        dmem_we;

  wire [31:0] imem_data = imem[imem_addr[11:2]];
  wire [11:0] da = {dmem_addr[11:2], 2'b00};
  assign dmem_rdata = {dmem[da+3], dmem[da+2], dmem[da+1], dmem[da]};

  riscv_core dut (
    .clk(clk), .rst(rst),
    .imem_addr(imem_addr), .imem_data(imem_data),
    .dmem_addr(dmem_addr), .dmem_wdata(dmem_wdata),
    .dmem_wstrb(dmem_wstrb), .dmem_we(dmem_we),
    .dmem_rdata(dmem_rdata)
  );

  always @(posedge clk) begin
    if (dmem_we) begin
      if (dmem_wstrb[0]) dmem[da]   <= dmem_wdata[7:0];
      if (dmem_wstrb[1]) dmem[da+1] <= dmem_wdata[15:8];
      if (dmem_wstrb[2]) dmem[da+2] <= dmem_wdata[23:16];
      if (dmem_wstrb[3]) dmem[da+3] <= dmem_wdata[31:24];
    end
  end

  reg [1023:0] hexfile, outfile;
  integer i, f, cycles;

  initial begin
    for (i = 0; i < 1024; i = i + 1) imem[i] = 32'h00000013; // NOP fill
    for (i = 0; i < 4096; i = i + 1) dmem[i] = 8'h00;
    if (!$value$plusargs("HEX=%s", hexfile)) begin
      $display("ERROR: +HEX=<file> required"); $finish;
    end
    if (!$value$plusargs("OUT=%s", outfile)) outfile = "out.txt";
    $readmemh(hexfile, imem);

    repeat (3) @(posedge clk);
    #1 rst = 0;

    cycles = 0;
    while (imem_data !== 32'h00100073 && cycles < 200000) begin
      @(posedge clk);
      cycles = cycles + 1;
    end

    if (cycles >= 200000) $display("TIMEOUT: no EBREAK after %0d cycles", cycles);

    f = $fopen(outfile, "w");
    for (i = 0; i < 32; i = i + 1)
      $fdisplay(f, "%08x", dut.rf.regs[i]);
    for (i = 0; i < 512; i = i + 1)
      $fdisplay(f, "%08x", {dmem[i*4+3], dmem[i*4+2], dmem[i*4+1], dmem[i*4]});
    $fclose(f);
    $display("DONE cycles=%0d", cycles);
    $finish;
  end
endmodule
