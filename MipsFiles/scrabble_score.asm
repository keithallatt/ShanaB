# ................................................................ #
.data
list: .word 1, 3, 3, 2, 1, 4, 2, 4, 1, 8, 5, 1, 3, 1, 1, 3, 10, 1, 1, 1, 1, 4, 4,  8, 4, 10
buffer: .space 80
enter_line: .asciiz "Enter a word: "
point_str: .asciiz "Your word is worth: "
# ---------------------------------------------------------------- #
.text
main:

	la $a0, enter_line
	li $v0, 4
	syscall

# ................................................................ #

    la $a0, buffer 				# load the buffer string address
    move $t0, $a0           	# Keep the address for later use in t0
    li $a1, 80              	# max 80 characters
    li $v0, 8               	# read string syscall
    syscall                 	# Read it!
# ................................................................ #

	la $a0, point_str
	li $v0, 4
	syscall

	li $t9, 0 						# running total
loop:
	lbu $t1, 0($t0)				# load byte at that address
	lbu $t8, 1($t0)				# load next too
	seq $a1, $t8, 10			# set equal if last one.
	
	beq $t1, 10, end			# end program at countdown

	li $t3, -97					# 
	add $t3, $t3, $t1			# offset ascii value to list index
	mul $t3, $t3, 4				# word align
	la $t4, list				# load the list address
	add $t3, $t3, $t4			# add offset to list address
	lw $t2, 0($t3)				# load word at appropriate address
	
	move $a0, $t2
	li $v0, 1
	syscall
		
	
	jal print_plus

	add $t9, $t9, $t2 			# add to running total

	addi $t0, $t0, 1			# go to next byte-wide address	
	j loop						# do it again!


print_plus:
	li $v0, 11
	
	li $a0, 32
	syscall

	beq $a1, 1, equal

	li $a0, 43
	syscall
	j after_equal
equal:
	li $a0, 61
	syscall

after_equal:


	li $a0, 32
	syscall

	jr $ra


# ................................................................ #
#   move $a0, $t0           	# the buffer address is kept by $t03
#	li $v0, 4               	# print string syscall
#   syscall                 	# print it!
# ................................................................ #
end:
	move $a0, $t9				# 	
	li $v0, 1					# set up to print int
	syscall						# print the value


    li $v0, 10              	# end program syscall
    syscall                 
# ---------------------------------------------------------------- #

exception:
	
			
    li $v0, 10              	# end program syscall
    syscall                 
