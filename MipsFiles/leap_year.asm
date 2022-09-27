.data

	prompt_year: .asciiz "Enter a year: "
	response_leap_1: .asciiz "The year "
	response_leap_2: .asciiz " is a leap year."
	response_leap_3: .asciiz " is not a leap year."
	
.text

main:
	li $v0, 4
	la $a0, prompt_year
	syscall
	

	li $v0, 5
	syscall
	
	move $t0, $v0  # $t0 = year input
	
	li $a0, 10
	li $v0, 11
	syscall # newline
	
	li $t1, 4
	div $t0, $t1
	mfhi $t2
	
	li $t1, 100
	div $t0, $t1
	mfhi $t3
	
	li $t1, 400
	div $t0, $t1
	mfhi $t4
	
	bnez $t2, not_leap  # if not div by 4, not a leap year
	beqz $t4, leap  # if div by 400, nullifies the div by 100 rule
	beqz $t3, not_leap # if not div by 400 and div by 100, not leap year

leap:	
	la $a0, response_leap_1
	li $v0, 4
	syscall
	
	li $v0, 1
	move $a0, $t0
	syscall
	
	la $a0, response_leap_2
	li $v0, 4
	syscall
	
	j end	
	
	
not_leap:
	la $a0, response_leap_1
	li $v0, 4
	syscall
	
	li $v0, 1
	move $a0, $t0
	syscall
	
	la $a0, response_leap_3
	li $v0, 4
	syscall
	
	
end:	
	li $v0, 10
	syscall    
