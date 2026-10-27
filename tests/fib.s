li x1, 0
li x2, 1
li x3, 10
loop:
beqz x3, done
add x4, x1, x2
mv x1, x2
mv x2, x4
addi x3, x3, -1
j loop
done:
ebreak
