# RV32I Single-Cycle CPU in Verilog

A single-cycle RISC-V RV32I core, plus the verification infrastructure around it:
a Python assembler, a Python golden-reference instruction-set simulator, constrained-random
program generation, and mutation testing of the test suite itself.

## Core (`rtl/`)
- `riscv_core.v`: single-cycle datapath, Harvard imem/dmem, byte-strobe stores, sign/zero-extended loads
- `alu.v`, `regfile.v`
- Implemented: LUI, AUIPC, JAL, JALR, all branches, LB/LH/LW/LBU/LHU, SB/SH/SW, all OP and OP-IMM
- Not implemented: FENCE, ECALL, CSRs, misaligned accesses, interrupts (EBREAK is the testbench stop marker)

## Verification
| Check | What it does |
|---|---|
| Directed tests (`tests/*.s`) | ALU, branches, load/store, jumps, Fibonacci, with hand-computed expected values |
| Random co-simulation | `tools/gen_random.py` makes constrained-random programs; final registers and 2 KB of data memory are compared against `tools/rviss.py` |
| Mutation testing | `tools/mutation_test.py` injects 16 RTL bugs one at a time; the regression must fail on each |
| Assembler cross-check | `tools/crosscheck_gnu.py` compares `rvasm.py` output with GNU `as -march=rv32i` |

## Results (Icarus Verilog 12)
- 5 directed + 300 random programs: all match the ISS
- Mutation testing: 16/16 injected bugs caught (first run caught 14/16; one survivor exposed a real test hole,
  a JALR missing its LSB clear, now covered; the other was an equivalent mutant)
- Assembler: 0 mismatches against GNU `as` on 105 programs

## Run
```
make test        # needs iverilog + python3
make mutation
make crosscheck  # optional, needs riscv binutils
```

## Known limitations
- The ISS and the RTL were written by the same person, so a shared misreading of the spec could hide.
  Mitigations: hand-computed known answers in directed tests, and the GNU assembler cross-check for encodings.
  Not yet run: the official riscv-tests / riscv-arch-test suites.
- Single-cycle, no pipeline, no timing/synthesis results yet.

## Next steps
- 5-stage pipeline with forwarding and hazard detection, verified against the same ISS
- Run riscv-arch-test
- Synthesize with Yosys for area/Fmax numbers
- UVM environment around the core (ties into the SystemVerilog/UVM work)
