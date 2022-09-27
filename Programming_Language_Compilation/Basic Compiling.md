
### Exit 

This one is easy, just have 

```
end:
	li $v0, 10          # end program syscall
	syscall
```

at end of file, and add

```
j end
```

wherever exit() is called.

### Basic Maths

- find order of operations
- put in prefix notation
- evaluate using temporary variables 

### Variable Declaration

- must have most inner label prepended to variable name to preserve scope