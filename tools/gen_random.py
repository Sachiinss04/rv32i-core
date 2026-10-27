#!/usr/bin/env python3
"""Constrained-random RV32I program generator.

Usage: gen_random.py SEED [N_INSTR] > prog.s

Constraints: destinations x1..x15 only (x31 is the data-memory base, 0x200);
loads/stores are naturally aligned and stay within base+[0,252]; branches and
JALs only go forward over a short block, so every program terminates.
"""
import random
import sys

R = ['add', 'sub', 'sll', 'slt', 'sltu', 'xor', 'srl', 'sra', 'or', 'and']
I = ['addi', 'slti', 'sltiu', 'xori', 'ori', 'andi']
SH = ['slli', 'srli', 'srai']
BR = ['beq', 'bne', 'blt', 'bge', 'bltu', 'bgeu']
LD = [('lb', 1), ('lbu', 1), ('lh', 2), ('lhu', 2), ('lw', 4)]
ST = [('sb', 1), ('sh', 2), ('sw', 4)]


def main():
    seed = int(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 150
    rnd = random.Random(seed)
    out = []
    reg_d = lambda: 'x%d' % rnd.randint(1, 15)
    reg_s = lambda: 'x%d' % rnd.randint(0, 15)

    out.append('li x31, 0x200')
    for r in range(1, 16):
        out.append('li x%d, %d' % (r, rnd.choice(
            [0, 1, -1, 0x7FFFFFFF, -0x80000000, rnd.randint(-2**31, 2**31 - 1),
             rnd.randint(-2048, 2047)])))

    def straight():
        k = rnd.random()
        if k < 0.35:
            return '%s %s, %s, %s' % (rnd.choice(R), reg_d(), reg_s(), reg_s())
        if k < 0.55:
            return '%s %s, %s, %d' % (rnd.choice(I), reg_d(), reg_s(), rnd.randint(-2048, 2047))
        if k < 0.65:
            return '%s %s, %s, %d' % (rnd.choice(SH), reg_d(), reg_s(), rnd.randint(0, 31))
        if k < 0.72:
            return 'lui %s, %d' % (reg_d(), rnd.randint(0, 0xFFFFF))
        if k < 0.76:
            return 'auipc %s, %d' % (reg_d(), rnd.randint(0, 0xFFFFF))
        if k < 0.88:
            m, sz = rnd.choice(ST)
            return '%s %s, %d(x31)' % (m, reg_s(), rnd.randrange(0, 256, sz))
        m, sz = rnd.choice(LD)
        return '%s %s, %d(x31)' % (m, reg_d(), rnd.randrange(0, 256, sz))

    lab = 0
    i = 0
    while i < n:
        if rnd.random() < 0.12:
            lab += 1
            k = rnd.randint(1, 4)
            if rnd.random() < 0.8:
                out.append('%s %s, %s, L%d' % (rnd.choice(BR), reg_s(), reg_s(), lab))
            else:
                out.append('jal %s, L%d' % (reg_d(), lab))
            for _ in range(k):
                out.append(straight())
            out.append('L%d:' % lab)
            i += k + 1
        else:
            out.append(straight())
            i += 1
    out.append('ebreak')
    print('\n'.join(out))


if __name__ == '__main__':
    main()
