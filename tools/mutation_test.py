#!/usr/bin/env python3
"""Mutation test: inject one RTL bug at a time and check the regression fails.

A surviving mutant means the test suite has a hole. Usage: mutation_test.py
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MUTANTS = [
    ('alu.v', '$signed(a) >>> b[4:0]', 'a >> b[4:0]', 'SRA behaves as SRL'),
    ('alu.v', '{31\'b0, ($signed(a) < $signed(b))}', '{31\'b0, (a < b)}', 'SLT unsigned'),
    ('alu.v', 'y = a - b;', 'y = a + b;', 'SUB behaves as ADD'),
    ('alu.v', 'y = a << b[4:0];', 'y = a << b[3:0];', 'shift amount truncated to 4 bits'),
    ('riscv_core.v', "3'b100:  take = ($signed(rs1_v) <  $signed(rs2_v));",
     "3'b100:  take = (rs1_v < rs2_v);", 'BLT unsigned'),
    ('riscv_core.v', "3'b111:  take = (rs1_v >= rs2_v);", "3'b111:  take = (rs1_v > rs2_v);",
     'BGEU off by one'),
    ('riscv_core.v', "& ~32'd1;", ";", 'JALR does not clear LSB'),
    ('riscv_core.v', "{{24{rsh[7]}},  rsh[7:0]}", "{24'b0, rsh[7:0]}", 'LB not sign extended'),
    ('riscv_core.v', "{{16{rsh[15]}}, rsh[15:0]}", "{16'b0, rsh[15:0]}", 'LH not sign extended'),
    ('riscv_core.v', "off[1] ? 4'b1100 : 4'b0011", "4'b0011", 'SH ignores upper half'),
    ('riscv_core.v', "4'b0001 << off", "4'b0001", 'SB ignores byte offset'),
    ('riscv_core.v', "wb = pc + imm_u;", "wb = imm_u;", 'AUIPC forgets PC'),
    ('riscv_core.v', "wb = pc4;", "wb = pc;", 'JAL link address wrong'),
    ('riscv_core.v', "inst[30:21], 1'b0}", "inst[30:21], 1'b1}", 'JAL immediate LSB'),
    ('regfile.v', [("(ra1 == 5'd0) ? 32'b0 : regs[ra1]", "regs[ra1]"),
                   ("if (we && wa != 5'd0)", "if (we)")], 'x0 writable and readable'),
    ('riscv_core.v', "(is_op & f7b5) ? 4'd1 : 4'd0", "f7b5 ? 4'd1 : 4'd0", 'ADDI with bit30 acts as SUB'),
]


def main():
    survivors = 0
    for entry in MUTANTS:
        fname, old, desc = entry[0], entry[1], entry[-1]
        new = entry[2] if len(entry) == 4 else None
        path = os.path.join(ROOT, 'rtl', fname)
        orig = open(path).read()
        pairs = old if isinstance(old, list) else [(old, new)]
        if any(o not in orig for o, _ in pairs):
            print('SKIP    %-40s (pattern not found)' % desc)
            continue
        shutil.copy(path, path + '.bak')
        try:
            mutated = orig
            for o, n in pairs:
                mutated = mutated.replace(o, n, 1)
            open(path, 'w').write(mutated)
            r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'run_tests.py'), '60'],
                               capture_output=True, text=True)
            caught = r.returncode != 0
        finally:
            shutil.move(path + '.bak', path)
        print('%-8s %s' % ('CAUGHT' if caught else 'SURVIVED', desc))
        survivors += (not caught)
    print('-' * 50)
    print('mutants: %d, survived: %d' % (len(MUTANTS), survivors))
    sys.exit(1 if survivors else 0)


if __name__ == '__main__':
    main()
