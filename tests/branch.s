li x1, 5
li x2, 5
li x3, -1
li x4, 1
li x10, 0
beq x1, x2, L1
j fail
L1: ori x10, x10, 1
bne x1, x4, L2
j fail
L2: ori x10, x10, 2
blt x3, x4, L3
j fail
L3: ori x10, x10, 4
bge x4, x3, L4
j fail
L4: ori x10, x10, 8
bltu x4, x3, L5
j fail
L5: ori x10, x10, 16
bgeu x3, x4, L6
j fail
L6: ori x10, x10, 32
bne x1, x2, fail
beq x1, x4, fail
blt x4, x3, fail
bltu x3, x4, fail
ori x10, x10, 64
ebreak
fail: li x10, -1
ebreak
