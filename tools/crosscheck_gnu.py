#!/usr/bin/env python3
"""Cross-check tools/rvasm.py against the GNU RISC-V assembler.

Requires binutils (riscv64-linux-gnu-as / -objcopy). Assembles every
directed test and 100 random programs with both assemblers and compares
the machine words. Skips (exit 0) if binutils is not installed.
"""
import glob
import os
import shutil
import struct
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import rvasm  # noqa: E402

AS = shutil.which('riscv64-linux-gnu-as') or shutil.which('riscv64-unknown-elf-as')
OBJCOPY = shutil.which('riscv64-linux-gnu-objcopy') or shutil.which('riscv64-unknown-elf-objcopy')


def gnu_words(text, tmp):
    s, o, b = [os.path.join(tmp, n) for n in ('p.s', 'p.o', 'p.bin')]
    # GNU needs ebreak spelled the same; labels like 'L1:' and 'end:' are fine
    open(s, 'w').write(text)
    subprocess.check_call([AS, '-march=rv32i', '-mabi=ilp32', '-o', o, s])
    subprocess.check_call([OBJCOPY, '-O', 'binary', '-j', '.text', o, b])
    data = open(b, 'rb').read()
    return list(struct.unpack('<%dI' % (len(data) // 4), data))


def main():
    if not AS or not OBJCOPY:
        print('SKIP: riscv binutils not installed')
        return 0
    progs = [(os.path.basename(p), open(p).read())
             for p in sorted(glob.glob(os.path.join(ROOT, 'tests', '*.s')))]
    gen = os.path.join(ROOT, 'tools', 'gen_random.py')
    for seed in range(1, 101):
        progs.append(('rand_%d' % seed,
                      subprocess.check_output([sys.executable, gen, str(seed)], text=True)))
    bad = 0
    with tempfile.TemporaryDirectory() as tmp:
        for name, text in progs:
            mine = rvasm.assemble(text)
            theirs = gnu_words(text, tmp)
            if mine != theirs:
                bad += 1
                for i, (m, t) in enumerate(zip(mine, theirs)):
                    if m != t:
                        print('MISMATCH %s word %d: mine=%08x gnu=%08x' % (name, i, m, t))
                        break
                else:
                    print('MISMATCH %s length mine=%d gnu=%d' % (name, len(mine), len(theirs)))
    print('assembler cross-check: %d programs, %d mismatches' % (len(progs), bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
