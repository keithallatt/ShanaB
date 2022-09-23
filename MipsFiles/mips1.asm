.data
	msg1: .asciiz "My name is Keith"
	
	valA: .float 8.32
	valB: .float -0.6234e4
.text

main:
	li $t0, 8

	mtc1 $t0, $f10
	cvt.s.w $f12, $f10
	li $v0, 2
	syscall
	
	
	li $v0, 10
	syscall    
	
	