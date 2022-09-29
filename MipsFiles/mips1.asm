# ---START----------------------------- #
# ---Compiled Code:-------------------- #
# int main(str[] args) {                #
#     int x, i;                         #
#     x = read_int();                   #
#     i = 0;                            #
#     while (i < x) {                   #
#         write(i);                     #
#         i = i + 1;                    #
#     }                                 #
#     write("Done");                    #
# }                                     #
# ------------------------------------- #
    .data                               #
built_in_status_code_str: .asciiz "\n\nProcess exited with status code "#
built_in_status_code: .word 0           #
    .text                               #
    .globl main                         #
main:                                   #
    sw $t0, 0($sp)                      # Push A0 onto global stack
    addi $sp, $sp, -4                   #
    addi $sp, $sp, 4                    # Pop global stack onto A0
    lw $t0, 0($sp)                      #
# ---END------------------------------- # 
end:                                    #
    li $v0, 4                           #
    la $a0, built_in_status_code_str    # print("Process exited with status code ")
    syscall                             #
    li $v0, 1                           #
    lw $a0, built_in_status_code        # print(f"{status_code}")
    syscall                             #
    li $v0, 10                          # end program syscall
    syscall                             #
# ---EXCEPTION------------------------- #
exception:                              #
    sw $a0, built_in_status_code        # move a0 to built_in_status_code variable
    j end                               # exit process
