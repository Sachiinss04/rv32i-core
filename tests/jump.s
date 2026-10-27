jal x1, func
li x6, 99
auipc x7, 0
addi x7, x7, 13
jalr x8, 0(x7)
li x9, 111
auipc x10, 0
jal x11, end
li x12, 7
end:
ebreak
func:
li x5, 42
jalr x0, 0(x1)
