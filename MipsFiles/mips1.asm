# ................................................................. #
#																	#
# int main(str[] args) {											#
# 	  int x, i;														#
# 	  x = read_int();												#
# 	  i = 0;														#
# 	  while (i < x) {												#
#     	  print(i);													#
#   	  i = i + 1;												#
# 	  }																#
#	  print("Done");												#
# }																	#
# ................................................................. #

	# push t0 onto stack
	# sw $t0, 0($sp)
	# addi $sp, $sp, -4
		
	# pop from stack into t0
	# addi $sp, $sp, 4
	# lw $t0, 0($sp)
	


# ........................START................................... #
	.data
built_in_status_code_str: .asciiz "\n\nProcess exited with status code "
built_in_status_code: .word 0


# ---------------------------------------------------------------- #
	.text
	.globl main

main:
	li $t0, 3
	

	.data							# initialize, 'x', 'i'
		main_x: .word 0
		main_i: .word 0
	.text
		
	li $v0, 5						# compute 'read_int()'
	syscall
	
	sw $v0, main_x					# 'x = read_int()'
	nop								# 'i = 0' by default

	lw $t0, main_i					# 'i' is used in condition
	lw $t1, main_x					# 'x' is used in condition
	
	
main_while_0:						# start of while loop
	bge $t0, $t1, main_while_0e		# while (i < 3) <=> until (i >= 3)
	

	li $v0, 1						# print call; i is of type integer
	move $a0, $t0					# copy i to address 0 register
	syscall
	li $v0, 11						# add char
	li $a0, 10						# char = "\n"
	syscall
	
	addi $t0, $t0, 1				# incremenent 'i' by 1
	
	j main_while_0
main_while_0e:						# end of while loop
	
	li $v0, 11						# "Done" is 'short' string, so ind. syscall
	li $a0, 'D'
	syscall						
	li $a0, 'o'
	syscall						
	li $a0, 'n'
	syscall						
	li $a0, 'e'
	syscall	
	li $a0, '\n'
	syscall	
						
	

# ..........................END................................... #
end:	
	li $v0, 4
	la $a0, built_in_status_code_str
	syscall

	li $v0, 1
	lw $a0, built_in_status_code
	syscall
	
    li $v0, 10              	# end program syscall
    syscall                 

# ................................................................ #
exception:
	# move a0 to built_in.status_code.
	sw $a0, built_in_status_code
	j end
