.data
	hello: .asciiz "Hello, World!"
.text
main:
	li $v0, 4		# Set syscall operation to print string
	la $a0, hello	# Add address to "Hello, World!" string
	syscall			# Print it!
	li $v0, 10		# Set syscall operation to end program.
	syscall    		# End it!