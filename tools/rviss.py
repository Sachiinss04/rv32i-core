#!/usr/bin/env python3
"""Golden-reference RV32I instruction-set simulator.

Decodes machine words independently of the assembler and writes the same
dump format as tb/tb_core.v: 32 registers then 512 data words (hex).
Data memory is 4 KB, byte addressed from 0 (matches the testbench).
Misaligned accesses are not supported (tests avoid them).
"""
import sys

M32 = 0xFFFFFFFF


def s32(x):
    x &= M32
    return x - (1 << 32) if x & 0x80000000 else x


def sext(v, bits):
    v &= (1 << bits) - 1
    return v - (1 << bits) if v & (1 << (bits - 1)) else v


def run(words, max_steps=200000):
    regs = [0] * 32
    mem = bytearray(4096)
    pc = 0
    steps = 0

    def rd8(a):
        return mem[a & 0xFFF]

    def wr8(a, v):
        mem[a & 0xFFF] = v & 0xFF

    while steps < max_steps:
        idx = pc >> 2
        w = words[idx] if idx < len(words) else 0x00000013
        if w == 0x00100073:
            break
        steps += 1
        op = w & 0x7F
        rd = (w >> 7) & 0x1F
        f3 = (w >> 12) & 7
        rs1 = (w >> 15) & 0x1F
        rs2 = (w >> 20) & 0x1F
        f7 = (w >> 25) & 0x7F
        a, b = regs[rs1], regs[rs2]
        imm_i = sext(w >> 20, 12)
        imm_s = sext(((w >> 25) << 5) | ((w >> 7) & 0x1F), 12)
        imm_b = sext((((w >> 31) & 1) << 12) | (((w >> 7) & 1) << 11) |
                     (((w >> 25) & 0x3F) << 5) | (((w >> 8) & 0xF) << 1), 13)
        imm_u = w & 0xFFFFF000
        imm_j = sext((((w >> 31) & 1) << 20) | (((w >> 12) & 0xFF) << 12) |
                     (((w >> 20) & 1) << 11) | (((w >> 21) & 0x3FF) << 1), 21)
        npc = (pc + 4) & M32
        res = None

        if op == 0x37:                      # LUI
            res = imm_u
        elif op == 0x17:                    # AUIPC
            res = (pc + imm_u) & M32
        elif op == 0x6F:                    # JAL
            res = npc
            npc = (pc + imm_j) & M32
        elif op == 0x67:                    # JALR
            res = npc
            npc = ((a + imm_i) & ~1) & M32
        elif op == 0x63:                    # BRANCH
            t = {0: a == b, 1: a != b, 4: s32(a) < s32(b), 5: s32(a) >= s32(b),
                 6: a < b, 7: a >= b}[f3]
            if t:
                npc = (pc + imm_b) & M32
        elif op == 0x03:                    # LOAD
            addr = (a + imm_i) & M32
            if f3 == 0:   res = sext(rd8(addr), 8) & M32
            elif f3 == 1: res = sext(rd8(addr) | (rd8(addr + 1) << 8), 16) & M32
            elif f3 == 2: res = (rd8(addr) | (rd8(addr + 1) << 8) |
                                 (rd8(addr + 2) << 16) | (rd8(addr + 3) << 24))
            elif f3 == 4: res = rd8(addr)
            elif f3 == 5: res = rd8(addr) | (rd8(addr + 1) << 8)
        elif op == 0x23:                    # STORE
            addr = (a + imm_s) & M32
            n = {0: 1, 1: 2, 2: 4}[f3]
            for i in range(n):
                wr8(addr + i, b >> (8 * i))
        elif op == 0x13 or op == 0x33:      # OP-IMM / OP
            y = imm_i & M32 if op == 0x13 else b
            sh = y & 0x1F
            alt = (w >> 30) & 1
            if f3 == 0:
                res = (a - y) & M32 if (op == 0x33 and alt) else (a + y) & M32
            elif f3 == 1: res = (a << sh) & M32
            elif f3 == 2: res = int(s32(a) < s32(y))
            elif f3 == 3: res = int(a < y)
            elif f3 == 4: res = a ^ y
            elif f3 == 5: res = (s32(a) >> sh) & M32 if alt else a >> sh
            elif f3 == 6: res = a | y
            elif f3 == 7: res = a & y
        if res is not None and rd != 0:
            regs[rd] = res & M32
        pc = npc
    return regs, mem, steps


def dump_lines(regs, mem):
    out = ['%08x' % r for r in regs]
    for i in range(512):
        out.append('%08x' % int.from_bytes(mem[i * 4:i * 4 + 4], 'little'))
    return out


if __name__ == '__main__':
    words = [int(l, 16) for l in open(sys.argv[1]) if l.strip()]
    regs, mem, _ = run(words)
    open(sys.argv[2], 'w').write('\n'.join(dump_lines(regs, mem)) + '\n')
