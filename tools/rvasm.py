#!/usr/bin/env python3
"""Minimal RV32I assembler. Usage: rvasm.py prog.s out.hex

Supports all RV32I base integer instructions (except FENCE/ECALL), labels,
and the pseudo-instructions: nop li mv j jr ret beqz bnez not neg ebreak.
Output is one 32-bit hex word per line (for $readmemh).
"""
import re
import sys

ABI = (['zero', 'ra', 'sp', 'gp', 'tp', 't0', 't1', 't2', 's0', 's1'] +
       ['a%d' % i for i in range(8)] + ['s%d' % i for i in range(2, 12)] +
       ['t3', 't4', 't5', 't6'])
REGS = {n: i for i, n in enumerate(ABI)}
REGS['fp'] = 8
REGS.update({'x%d' % i: i for i in range(32)})

R_OPS = {'add': (0x00, 0), 'sub': (0x20, 0), 'sll': (0x00, 1), 'slt': (0x00, 2),
         'sltu': (0x00, 3), 'xor': (0x00, 4), 'srl': (0x00, 5), 'sra': (0x20, 5),
         'or': (0x00, 6), 'and': (0x00, 7)}
I_OPS = {'addi': 0, 'slti': 2, 'sltiu': 3, 'xori': 4, 'ori': 6, 'andi': 7}
SH_OPS = {'slli': (0x00, 1), 'srli': (0x00, 5), 'srai': (0x20, 5)}
LOADS = {'lb': 0, 'lh': 1, 'lw': 2, 'lbu': 4, 'lhu': 5}
STORES = {'sb': 0, 'sh': 1, 'sw': 2}
BRANCH = {'beq': 0, 'bne': 1, 'blt': 4, 'bge': 5, 'bltu': 6, 'bgeu': 7}
EBREAK = 0x00100073


def reg(s):
    return REGS[s.strip()]


def wrap32(v):
    return ((v + (1 << 31)) % (1 << 32)) - (1 << 31)


def r_type(f7, rs2, rs1, f3, rd, op):
    return (f7 << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | op


def i_type(imm, rs1, f3, rd, op):
    assert -2048 <= imm < 2048, "I-imm out of range: %d" % imm
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | op


def s_type(imm, rs2, rs1, f3, op):
    assert -2048 <= imm < 2048, "S-imm out of range: %d" % imm
    return (((imm >> 5) & 0x7F) << 25) | (rs2 << 20) | (rs1 << 15) | \
           (f3 << 12) | ((imm & 0x1F) << 7) | op


def b_type(imm, rs2, rs1, f3, op):
    assert -4096 <= imm < 4096 and imm % 2 == 0, "B-imm out of range: %d" % imm
    return (((imm >> 12) & 1) << 31) | (((imm >> 5) & 0x3F) << 25) | (rs2 << 20) | \
           (rs1 << 15) | (f3 << 12) | (((imm >> 1) & 0xF) << 8) | \
           (((imm >> 11) & 1) << 7) | op


def u_type(imm, rd, op):
    return ((imm & 0xFFFFF) << 12) | (rd << 7) | op


def j_type(imm, rd, op):
    assert -(1 << 20) <= imm < (1 << 20) and imm % 2 == 0, "J-imm out of range"
    return (((imm >> 20) & 1) << 31) | (((imm >> 1) & 0x3FF) << 21) | \
           (((imm >> 11) & 1) << 20) | (((imm >> 12) & 0xFF) << 12) | (rd << 7) | op


def split_args(s):
    return [a.strip() for a in s.split(',')] if s.strip() else []


def expand(mn, args):
    """Expand pseudo-instructions into base instructions."""
    if mn == 'nop':
        return [('addi', ['x0', 'x0', '0'])]
    if mn == 'mv':
        return [('addi', [args[0], args[1], '0'])]
    if mn == 'not':
        return [('xori', [args[0], args[1], '-1'])]
    if mn == 'neg':
        return [('sub', [args[0], 'x0', args[1]])]
    if mn == 'j':
        return [('jal', ['x0', args[0]])]
    if mn == 'jr':
        return [('jalr', ['x0', '0(%s)' % args[0]])]
    if mn == 'ret':
        return [('jalr', ['x0', '0(ra)'])]
    if mn == 'beqz':
        return [('beq', [args[0], 'x0', args[1]])]
    if mn == 'bnez':
        return [('bne', [args[0], 'x0', args[1]])]
    if mn == 'jal' and len(args) == 1:
        return [('jal', ['ra', args[0]])]
    if mn == 'jalr' and len(args) == 1:
        return [('jalr', ['ra', '0(%s)' % args[0]])]
    if mn == 'li':
        v = wrap32(int(args[1], 0))
        if -2048 <= v < 2048:
            return [('addi', [args[0], 'x0', str(v)])]
        lo = ((v & 0xFFF) ^ 0x800) - 0x800          # sign-extended low 12
        hi = ((v - lo) >> 12) & 0xFFFFF
        if lo == 0:
            return [('lui', [args[0], str(hi)])]
        return [('lui', [args[0], str(hi)]), ('addi', [args[0], args[0], str(lo)])]
    return [(mn, args)]


def assemble(text):
    items, labels, pc = [], {}, 0
    for raw in text.splitlines():
        line = raw.split('#')[0].strip()
        while ':' in line:
            lab, line = line.split(':', 1)
            labels[lab.strip()] = pc
            line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        mn = parts[0].lower()
        args = split_args(parts[1]) if len(parts) > 1 else []
        if mn == 'ebreak':
            items.append((pc, 'ebreak', [])); pc += 4; continue
        for m, a in expand(mn, args):
            items.append((pc, m, a)); pc += 4

    def val(tok, pc_here):
        tok = tok.strip()
        if tok in labels:
            return labels[tok] - pc_here
        return int(tok, 0)

    def mem(tok):
        m = re.match(r'^(-?\w+)\((\w+)\)$', tok.strip())
        return int(m.group(1), 0), reg(m.group(2))

    words = []
    for pc, mn, a in items:
        if mn == 'ebreak':
            w = EBREAK
        elif mn in R_OPS:
            f7, f3 = R_OPS[mn]; w = r_type(f7, reg(a[2]), reg(a[1]), f3, reg(a[0]), 0x33)
        elif mn in I_OPS:
            w = i_type(int(a[2], 0), reg(a[1]), I_OPS[mn], reg(a[0]), 0x13)
        elif mn in SH_OPS:
            f7, f3 = SH_OPS[mn]; sh = int(a[2], 0)
            assert 0 <= sh < 32
            w = r_type(f7, sh, reg(a[1]), f3, reg(a[0]), 0x13)
        elif mn in LOADS:
            imm, rs1 = mem(a[1]); w = i_type(imm, rs1, LOADS[mn], reg(a[0]), 0x03)
        elif mn in STORES:
            imm, rs1 = mem(a[1]); w = s_type(imm, reg(a[0]), rs1, STORES[mn], 0x23)
        elif mn in BRANCH:
            w = b_type(val(a[2], pc), reg(a[1]), reg(a[0]), BRANCH[mn], 0x63)
        elif mn == 'lui':
            w = u_type(int(a[1], 0), reg(a[0]), 0x37)
        elif mn == 'auipc':
            w = u_type(int(a[1], 0), reg(a[0]), 0x17)
        elif mn == 'jal':
            w = j_type(val(a[1], pc), reg(a[0]), 0x6F)
        elif mn == 'jalr':
            imm, rs1 = mem(a[1]); w = i_type(imm, rs1, 0, reg(a[0]), 0x67)
        else:
            raise SystemExit("unknown instruction: %s %s" % (mn, a))
        words.append(w & 0xFFFFFFFF)
    return words


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    ws = assemble(open(src).read())
    with open(dst, 'w') as f:
        for w in ws:
            f.write('%08x\n' % w)
