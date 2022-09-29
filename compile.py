import re
import pprint
import expression_analyzer

variable_name_re = re.compile(r"[a-zA-Z_][a-zA-Z_0-9]*")
typed_variable_re = re.compile(rf"(int|float|char|void)\s({variable_name_re.pattern})")
typed_variable_list_re = re.compile(
    rf"((int|float|char)\s*(\[\d+])?)\s(\s*{variable_name_re.pattern}(\s*,\s*{variable_name_re.pattern})*)")
func_def_re = re.compile(rf"{typed_variable_re.pattern}\(({typed_variable_re}(,\s*{typed_variable_re})*)?\)")
assignment_re = re.compile(rf"({variable_name_re.pattern})\s*=\s*(.+)")
control_flow_re = re.compile(rf"(while|if)\s*(\(.+\))")
write_re = re.compile(r'write\(((-?[1-9]\d*|0)|(-?\d+\.\d*)|(\"(([^"\n]|\\")*[^\\])?\")|([a-zA-Z_][a-zA-Z_0-9]*))\)')
return_re = re.compile(r"return (.+)")

TEMP_REGISTERS = [
    f"$t{i}" for i in range(10)
]
SAVED_REGISTERS = [
    f"$s{i}" for i in range(8)
]


START_OF_BODY = f"""
# ---START{'-'*29} #
""".strip()

DIV_LINE = f"""
# {'-'*37} #
""".strip()


def title_line(text):
    return f"# ---{text}{'-'*(34 - len(text))} #"


END_OF_BODY = f"""
# ---END{'-'*31} # """"""
end:
    li $v0, 4                           
    la $a0, built_in_status_code_str    # print("Process exited with status code ")
    syscall                             
    li $v0, 1                           
    lw $a0, built_in_status_code        # print(f"{status_code}")
    syscall                             
    li $v0, 10                          # end program syscall
    syscall                            
"""f"""# ---EXCEPTION{'-'*25} #
exception:
    sw $a0, built_in_status_code        # move a0 to built_in_status_code variable
    j end                               # exit process
""".strip()

PUSH_A0_TO_STACK = """
    sw $t0, 0($sp)          # Push A0 onto global stack
    addi $sp, $sp, -4
"""[1:].rstrip()

POP_STACK_TO_A0 = """
    addi $sp, $sp, 4        # Pop global stack onto A0
    lw $t0, 0($sp)
"""[1:].rstrip()


def comment_block(com, d=96, dual_side=False):
    lines = com.split("\n")
    lines = sum([
        [line[i:i+d] for i in range(0, len(line), d)] for line in lines
    ], [])

    if all([line.startswith("#") or not line.strip() for line in lines]):
        return com

    lines = ["# " + line + (" #" if dual_side else "") for line in lines]
    return "\n".join(lines)


def align_comments(block, distance=40):
    # final comment block will be at char_pos = distance
    lines = block.split("\n")

    lines = [
        ("#"+line.split("#")[-1], line) if "#" in line else (" ", line+" ") for line in lines
    ]
    lines = [
        line[:-len(last)].rstrip().ljust(distance) + last for last, line in lines
    ]
    return "\n".join(lines)


EXAMPLE_CODE_BLOCK = """
int main() {
    write(-3);
    write(1.3);
    write("Done");
}
"""


def tokenize1(code):
    bracket_level = [0]
    for c in code:
        bracket_level.append(bracket_level[-1] + {"{": 1, "}": -1}.get(c, 0))
    if any([b < 0 for b in bracket_level]):
        raise Exception("Mismatched Brackets")

    bracket_level.pop(0)
    bracket_level = [int(not not b) for b in bracket_level]
    l0, l1 = [], []

    while bracket_level:
        if 1 not in bracket_level:
            l0.append(len(bracket_level))
            break
        else:
            l0.append(bracket_level.index(1))
            bracket_level = bracket_level[l0[-1]:]

        if 0 not in bracket_level:
            l1.append(len(bracket_level))
            break
        else:
            l1.append(bracket_level.index(0))
            bracket_level = bracket_level[l1[-1]:]

    tokens = []

    while l0 + l1:
        co = l0.pop(0)
        tokens += code[:co].split(";")
        code = code[co+1:]

        if l1:
            co = l1.pop(0)
            tokens.append(tokenize1(code[:co].lstrip("{").rstrip("}")))
            code = code[co+1:]
        else:
            break

    def deep_strip(lst):
        return [
            l.strip() if isinstance(l, str) else deep_strip(l) for l in lst if (l.strip() if isinstance(l, str) else l)
        ]

    return deep_strip(tokens)


def tokenize2(ts):
    nts = []
    while ts:
        token = ts.pop(0)
        z = re.match(func_def_re, token.strip())
        if z is not None:
            ret_type = z.group(1)
            func_name = z.group(2)

            nts.append({"type": "Function", "header": func_name, "return_type": ret_type,
                        "signature": token, "body": tokenize2(ts.pop(0))})
            continue
        z = re.match(control_flow_re, token.strip())
        if z is not None:
            nts.append({"type": "Control Flow", "header": z.group(1), 'condition': z.group(2),
                        "token": token, "body": tokenize2(ts.pop(0))})
            continue
        z = re.match(typed_variable_list_re, token.strip())
        if z is not None:
            _type = z.group(2)
            array_part = z.group(3)
            arr_size = None
            if array_part:
                arr_size = int(array_part[1:-1])
                if arr_size <= 0:
                    raise Exception("Array dimension out of bounds.")
                _type += '[]'
            _vars = z.group(4)

            _vars = [v.strip() for v in _vars.split(",")]

            nts.append({"type": "Variable Initialization", "header": str(_type) + ", " + str(_vars),
                        "variables": _vars, "var_type": _type, "arr_size": arr_size, "token": token})
            continue

        z = re.match(assignment_re, token.strip())
        if z is not None:
            nts.append({"type": "Assignment", "header": z.group(1), "body": z.group(2)})
            continue

        z = re.match(write_re, token.strip())
        if z is not None:
            gs = list(z.groups())

            target = gs.pop(0)
            index = gs.index(target)
            string_contents = gs[3]
            write_type = [
                "Integer", "Float", "Char", "-string contents-", "-string contents-", "Variable"
            ][index]

            nts.append({"type": "Write", "header": token, "body": target,
                        "data_type": write_type, "string_contents": string_contents})
            continue
        z = re.match(return_re, token.strip())
        if z is not None:
            nts.append({"type": "Return", "header": token, "body": z.groups()})
            continue

        raise NotImplementedError(f"statement {repr(token)} not parsable.")
    return nts


def compile_snb(tokens, scope=None, registers=None, variables=None, global_level=True):
    if scope is None:
        scope = ["global"]
    if registers is None:
        # registers are used to temporarily store variables.
        registers = dict()
    if variables is None:
        # registers are used to temporarily store variables.
        variables = dict()

    data_lines = [
        "built_in_status_code_str: .asciiz \"\\n\\nProcess exited with status code \"",
        "built_in_status_code: .word 0"
    ] if global_level else []
    code_lines = []

    for t in tokens:
        statement_type = t.get("type", None)
        if statement_type is None:
            raise Exception(f"Statement malformed. Token={t}")

        if statement_type == "Function":
            func_name = t['header']
            func_label = "_".join(scope + [func_name]) + ":"
            func_label_end = "_".join(scope + [func_name, 'exit']) + ":"
            func_jump = f"j {func_label_end[:-1]}"
            statement_lines = [func_jump, func_label]

            body = t['body']

            dl, cl = compile_snb(body, scope + [func_name], registers, variables, False)
            data_lines += dl
            statement_lines += cl
            statement_lines.append(func_label_end)
            code_lines += statement_lines
        elif statement_type == "Variable Initialization":
            data_section = []
            var_type, vs = t['var_type'], t['variables']
            is_array = False
            array_dim = None
            if var_type.endswith("[]"):
                is_array = True
                array_dim = t['arr_size']

            data_size_b = {
                "int": 4,  # word
                "float": 4,  # word
                "char": 1,    # characters are bytes.
            }

            for v in vs:
                variables[f"{'_'.join(scope)}_{v}"] = var_type + ("[]" if is_array else "")

            data_size = data_size_b[var_type]
            var_type = ".byte '\\n'" if var_type == "char" else ".word 0"

            if is_array:
                data_size *= array_dim
                var_type = f".space {data_size}"

            data_section += [f"{'_'.join(scope)}_{v}: {var_type}   # {t['token']};" for v in vs]
            data_lines += data_section
        elif statement_type == "Assignment":
            unused_temps = [r for r in TEMP_REGISTERS if r not in registers.keys()]
            if not unused_temps:
                unused_temps = [r for r in SAVED_REGISTERS if r not in registers.keys()]
            if not unused_temps:
                raise Exception("Register Overload")

            temp1 = unused_temps.pop(0)
            registers[temp1] = "Assignment temp 1"
            var_name = "_".join(scope + [t['header']])
            assign_lines = [
                f"li {temp1}, {t['body']}",
                f"sw {temp1}, {var_name}  # {t['header']} = {t['body']};"
            ]

            registers.pop(temp1)
            code_lines += assign_lines
        elif statement_type == "Control Flow":
            print(t)
            condition = t['condition']
            print(condition)
            tks = expression_analyzer.tokenize_expression(condition[1:-1])
            print(tks)

            if t['header'] == 'while':
                # do while
                pass
            elif t['header'] == 'if':
                # do if
                pass
            else:
                raise Exception(f"Invalid Control Flow {t['header']}")
        elif statement_type == "Write":
            body = t['body']
            sc = t['string_contents']
            data_type = t['data_type'].lower()
            ndl = []
            write_lines = []

            if data_type == "variable":
                _s = scope[::]

                vn = "_".join(_s + [body])
                while vn not in variables.keys() and _s:
                    _s.pop(-1)
                    vn = "_".join(_s + [body])
                if not _s:
                    raise Exception(f"Variable {body} not found.")

                vn_d = variables[vn]
                print(vn, vn_d)
                if vn_d == "char":
                    write_lines.append(f"li $v0, 4")
                    write_lines.append(f"la $a0, {vn}")
                elif vn_d == "int":
                    write_lines.append(f"li $v0, 1")
                    write_lines.append(f"lw $a0, {vn}")
                elif vn_d == "float":
                    write_lines.append(f"li $v0, 2")
                    write_lines.append(f"lw $f12, {vn}")
            if data_type == "integer":
                # v0 = 1
                write_lines += [
                    "li $v0, 1",
                    f"li $a0, {body}",
                    "syscall"
                ]
            if data_type == "float":
                fname = "_".join(scope) + "_f"
                f_i = 0
                dl_names = [l[:l.index(":")] for l in data_lines]
                while f"{fname}{f_i}" in dl_names:
                    f_i += 1
                fname = f"{fname}{f_i}"

                data_lines.append(f"{fname}: .float {body}")
                write_lines += [
                    # f"la $v0, {fname}",
                    "li $v0, 2",
                    f"l.s $f12, {fname}",
                    "syscall"
                ]
                data_lines += dl_names
            if data_type == "char":
                # v0 = 4
                print(str)
                write_lines.append("li $v0, 11")
                for c in sc:
                    write_lines.append(f"li $a0, {ord(c)}")
                    write_lines.append("syscall")

            code_lines += write_lines + [
                "li $v0, 11",
                "li $a0, 10",
                "syscall"
            ]

    if not global_level:
        return data_lines, code_lines
    return ["    .data"] + data_lines + ["    .text", "j global_main"] + code_lines


if __name__ == '__main__':
    t1s = tokenize1(EXAMPLE_CODE_BLOCK)
    t2s = tokenize2(t1s)
    compiled = compile_snb(t2s)

    print('-'*30)
    # print(*compiled, sep="\n")
    # exit(0)
    print(align_comments(
        "\n".join([
            START_OF_BODY,
            title_line("Compiled Code:"),
            comment_block(EXAMPLE_CODE_BLOCK, dual_side=True),
            DIV_LINE,
            *compiled,
            END_OF_BODY
        ])))
