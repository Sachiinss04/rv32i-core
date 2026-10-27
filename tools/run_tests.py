#!/usr/bin/env python3
"""Regression runner.

For every program (directed tests/*.s plus N random programs):
  1. assemble to hex
  2. run the RTL (Icarus) and the Python ISS
  3. compare all 32 registers and 512 data words
Directed tests additionally check hand-computed known answers, so a bug
shared by the ISS and the RTL cannot hide.

Usage: run_tests.py [N_RANDOM] (default 200)
"""
import glob
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import rvasm  # noqa: E402
import rviss  # noqa: E402

BUILD = os.path.join(ROOT, 'sim', 'build')
os.makedirs(BUILD, exist_ok=True)

# hand-computed expected register values for directed tests
KNOWN = {
    'alu': {4: 103, 5: 97, 6: 24, 7: 1, 8: 0, 9: 103, 10: 0x1FFFFFFF,
            11: 0xFFFFFFFF, 12: 103, 13: 0, 14: 99, 15: 1, 16: 1,
            17: 0xFFFFFF9B, 18: 48, 19: 0x0FFFFFFF, 20: 0xFFFFFFFF,
            21: 0x12345000, 22: 0x12345678, 23: 0x80000FFF},
    'branch': {10: 127},
    'loadstore': {3: 0xDEADBEEF, 4: 0xFFFFFFEF, 5: 0xEF, 6: 0xFFFFFFBE,
                  7: 0xDE, 8: 0xFFFFBEEF, 9: 0xBEEF, 10: 0xFFFFDEAD,
                  11: 0xDEAD, 12: 0xDEAD00EF, 14: 0x123400EF, 15: 0x34000000},
    'jump': {1: 4, 5: 42, 6: 99},
    'fib': {1: 55, 2: 89, 3: 0},
}


def build_rtl():
    exe = os.path.join(BUILD, 'core.vvp')
    srcs = [os.path.join(ROOT, p) for p in
            ('rtl/alu.v', 'rtl/regfile.v', 'rtl/riscv_core.v', 'tb/tb_core.v')]
    subprocess.check_call(['iverilog', '-g2012', '-o', exe] + srcs)
    return exe


def run_one(exe, name, asm_text, known=None):
    words = rvasm.assemble(asm_text)
    hexf = os.path.join(BUILD, name + '.hex')
    outf = os.path.join(BUILD, name + '.rtl.txt')
    with open(hexf, 'w') as f:
        f.write('\n'.join('%08x' % w for w in words) + '\n')

    p = subprocess.run(['vvp', exe, '+HEX=' + hexf, '+OUT=' + outf],
                       capture_output=True, text=True)
    if 'TIMEOUT' in p.stdout:
        return False, 'RTL timeout'

    regs, mem, _ = rviss.run(words)
    exp = rviss.dump_lines(regs, mem)
    got = open(outf).read().split()
    if got != exp:
        for i, (g, e) in enumerate(zip(got, exp)):
            if g != e:
                where = 'x%d' % i if i < 32 else 'dmem[0x%x]' % ((i - 32) * 4)
                return False, 'ISS/RTL mismatch at %s: rtl=%s iss=%s' % (where, g, e)
        return False, 'ISS/RTL length mismatch'
    if known:
        for r, v in known.items():
            if int(got[r], 16) != v:
                return False, 'known-answer fail x%d: got %s want %08x' % (r, got[r], v)
    return True, ''


def main():
    n_rand = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    exe = build_rtl()
    passed = failed = 0

    for path in sorted(glob.glob(os.path.join(ROOT, 'tests', '*.s'))):
        name = os.path.basename(path)[:-2]
        ok, msg = run_one(exe, name, open(path).read(), KNOWN.get(name))
        print('%-6s directed %-10s %s' % ('PASS' if ok else 'FAIL', name, msg))
        passed += ok
        failed += (not ok)

    gen = os.path.join(ROOT, 'tools', 'gen_random.py')
    rfail = 0
    for seed in range(1, n_rand + 1):
        text = subprocess.check_output([sys.executable, gen, str(seed)], text=True)
        ok, msg = run_one(exe, 'rand_%d' % seed, text)
        if not ok:
            rfail += 1
            print('FAIL   random seed=%d %s' % (seed, msg))
    print('PASS   random: %d/%d programs matched the ISS' % (n_rand - rfail, n_rand))
    passed += n_rand - rfail
    failed += rfail

    print('-' * 50)
    print('TOTAL passed=%d failed=%d' % (passed, failed))
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
