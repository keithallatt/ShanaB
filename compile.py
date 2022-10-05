import re
# import pprint
import subprocess

import expression_analyzer

variable_name_re = re.compile(r"[a-zA-Z_][a-zA-Z_0-9]*")
typed_variable_re = re.compile(rf"(int|float|char|void)\s({variable_name_re.pattern})")
typed_variable_list_re = re.compile(
    rf"((int|float|char)?\s*(\[\d+])?)\s(\s*{variable_name_re.pattern}(\s*,\s*{variable_name_re.pattern})*)")
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
FLOAT_REGISTERS = [
    f"$f{i}" for i in range(32)
]

START_OF_BODY = f"""
# ---START{'-' * 29} #
""".strip()

DIV_LINE = f"""
# {'-' * 37} #
""".strip()


def title_line(text):
    return f"# ---{text}{'-' * (34 - len(text))} #"


END_OF_BODY = f"""
# ---END{'-' * 31} # """"""
end:
    li $v0, 4                           
    la $a0, built_in_scr                # print("Process exited with status code ")
    syscall                             
    li $v0, 1                           
    lw $a0, built_in_sc                 # print(f"{status_code}")
    syscall                             
    li $v0, 10                          # end program syscall
    syscall                            
"""f"""# ---EXCEPTION{'-' * 25} #
exception:
    sw $a0, built_in_sc                 # move a0 to built_in_status_code variable
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
    lns = com.split("\n")
    lns = sum([
        [line[i:i + d] for i in range(0, len(line), d)] for line in lns
    ], [])

    if all([line.startswith("#") or not line.strip() for line in lns]):
        return com

    lns = ["# " + line + (" #" if dual_side else "") for line in lns]
    return "\n".join(lns)


def align_comments(block, distance=40):
    # final comment block will be at char_pos = distance
    lns = block.split("\n")

    lns = [
        ("#" + line.split("#")[-1], line) if "#" in line else (" ", line + " ") for line in lns
    ]
    lns = [
        line[:-len(last)].rstrip().ljust(distance) + last for last, line in lns
    ]
    return "\n".join(lns)


EXAMPLE_CODE_BLOCK = """
int main() {
    float x, y, z;
    x = 3;
    y = 2;
    z = x * (x < y) + y * (y <= x);
    write(z);
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
        code = code[co + 1:]

        if l1:
            co = l1.pop(0)
            tokens.append(tokenize1(code[:co].lstrip("{").rstrip("}")))
            code = code[co + 1:]
        else:
            break

    def deep_strip(lst):
        return [
            ln.strip() if isinstance(ln, str) else deep_strip(ln)
            for ln in lst if (ln.strip() if isinstance(ln, str) else ln)
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


# TEMPORARY
condition_counter = 0
if_counter = 0
while_counter = 0


def compile_snb(tokens, scope=None, registers=None, variables=None, global_level=True):
    # global condition_counter
    if scope is None:
        scope = ["global"]
    if registers is None:
        # registers are used to temporarily store variables.
        registers = dict()
    if variables is None:
        # registers are used to temporarily store variables.
        variables = dict()

    data_lines = [
        "built_in_scr: .asciiz \"\\nExited with status code \"",
        "built_in_sc: .word 0"
    ] if global_level else []
    code_lines = []

    for t in tokens:
        statement_type = t.get("type", None)
        if statement_type is None:
            raise Exception(f"Statement malformed. Token={t}")

        if 'token' in t.keys():
            headline = t['token']
        elif t['type'] == 'Assignment':
            headline = '{} = {}'.format(t['header'], t['body'])
        else:
            headline = t['header']

        code_lines.append(f"# --- {headline}; #")
        if statement_type == "Function":
            func_name = t['header']
            func_label = ".".join(scope + [func_name]) + ":"
            func_label_end = ".".join(scope + [func_name, 'exit']) + ":"
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
                "char": 1,  # characters are bytes.
            }

            for v in vs:
                variables[f"{'.'.join(scope + [v])}"] = var_type + ("[]" if is_array else "")

            data_size = data_size_b[var_type]
            var_type = ".byte '\\n'" if var_type == "char" else ".word 0"

            if is_array:
                data_size *= array_dim
                var_type = f".space {data_size}"

            data_section += [f"{'.'.join(scope + [v])}: {var_type}   # {t['token']};" for v in vs]
            data_lines += data_section
        elif statement_type == "Assignment":
            unused_temps = [r for r in TEMP_REGISTERS if r not in registers.keys()]
            # unused_floats = [f for f in FLOAT_REGISTERS if f not in registers.keys()]
            if not unused_temps:
                unused_temps = [r for r in SAVED_REGISTERS if r not in registers.keys()]
            if not unused_temps:
                raise Exception("Register Overload")

            var_name = ".".join(scope + [t['header']])

            body = t['body']
            body = expression_analyzer.tokenize_expression(body)

            # print(body)
            assign_lines = []

            # print(body)
            # t_regs = [f"$t{t}" for t in range(10)]
            # f_regs = [f"$f{f}" for f in range(32)]

            LOAD_INTO = "$t1"
            SWAP_REG = "$t0"

            def process_tree(tr, _vars=None):
                global condition_counter
                if _vars is None:
                    _vars = {
                        LOAD_INTO: 'load var into',
                        SWAP_REG: "swap register"
                    }
                _cls = []
                load_into = None

                while isinstance(tr, list) and len(tr) == 1:
                    tr = tr[0]

                if len(tr) == 4:
                    tr = [tr[0], tr[1] + tr[2], tr[3]]

                if len(tr) == 1 or isinstance(tr, dict):  # [dict] or dict
                    t = tr
                    if isinstance(tr, list):
                        t = tr[0]
                    try:
                        if t['type'] == "int literal":
                            i = 0
                            while f"$t{i}" in _vars.keys():
                                i += 1
                            if i >= 10:
                                raise Exception("Register overload")
                            _cls.append(f"li $t{i}, {t['token']}")

                            load_into = f"$t{i}"
                            _vars[load_into] = t['token']
                        elif t['type'] == "float literal":
                            i = 0
                            while f"$f{i}" in _vars.keys():
                                i += 1
                            if i >= 32:
                                raise Exception("Register overload")

                            lf = 0
                            dl_vars = [x.strip().split(":")[0] for x in data_lines]
                            lit_name = f"literal.float{lf}"
                            while lit_name in dl_vars:
                                lf += 1
                                lit_name = f"literal.float{lf}"

                            data_lines.append(f"{lit_name}: .float {t['token']}")
                            _cls.append(f"l.s $f{i}, {lit_name}  # load {t['token']}")

                            load_into = f"$f{i}"
                            _vars[load_into] = t['token']
                        elif t['type'] == "variable":
                            _s = scope[::]

                            vn = ".".join(_s + [t['token']])
                            while vn not in variables.keys():
                                if not _s:
                                    raise Exception(f"Variable not found: {t['token']}")
                                _s.pop(-1)
                                vn = ".".join(_s + [t['token']])

                            if variables[vn] == "int":
                                i = 0
                                while f"$t{i}" in _vars.keys():
                                    i += 1
                                if i >= 10:
                                    raise Exception("Register overload")

                                load_into = f"$t{i}"
                                _vars[load_into] = t['token']
                                _cls.append(f"lw {load_into}, {vn}")
                            elif variables[vn] == "float":
                                i = 0
                                while f"$f{i}" in _vars.keys():
                                    i += 1
                                if i >= 32:
                                    raise Exception("Register overload")

                                load_into = f"$f{i}"
                                _vars[load_into] = t['token']
                                _cls.append(f"l.s {load_into}, {vn}")
                        else:
                            raise NotImplementedError(f"{t['type']=}")
                    except TypeError as e:
                        print("---")
                        print(tr)
                        print(e)
                        exit(1)
                elif len(tr) == 2:
                    assert tr[1].strip() == "!"
                    t = tr[0]['token']
                    _s = scope[::]
                    vn = ".".join(_s + [t])
                    while vn not in variables:
                        if not _s:
                            raise Exception(f"Variable not found: {t=}")
                        _s.pop(-1)
                        vn = ".".join(_s + [t])

                    vt = variables[vn]
                    # print(f"{vt=}")
                    if vt == "int":
                        i = 0
                        while f"$t{i}" in _vars.keys():
                            i += 1
                        if i >= 10:
                            raise Exception("Register overload")

                        load_into = f"$t{i}"
                        _vars[load_into] = t['token']
                        _cls.append(f"lw {load_into}, {vn}")
                        _cls.append(f"neg {load_into}, {load_into}")
                    if vt == "float":
                        i = 0
                        while f"$f{i}" in _vars.keys():
                            i += 1
                        if i >= 32:
                            raise Exception("Register overload")

                        load_into = f"$f{i}"
                        _vars[load_into] = t['token']
                        _cls.append(f"l.s {load_into}, {vn}")
                        _cls.append(f"neg.s {load_into}, {load_into}")
                    if vt == "char":
                        i = 0
                        while f"$t{i}" in _vars.keys():
                            i += 1
                        if i >= 10:
                            raise Exception("Register overload")

                        load_into = f"$t{i}"
                        _vars[load_into] = t['token']

                        _cls.append(f"la {load_into}, {vn}")
                        _cls.append(f"lw {load_into}, ({load_into})")
                        _cls.append(f"neg {load_into}, {load_into}")
                elif len(tr) == 3:
                    l, o, r = tr
                    # print(f"{l=}, {r=}, {o=}", "-x-x-")
                    for flag, var in enumerate([l, r]):
                        _v = None

                        cl, vl, _v = process_tree(var, _vars)
                        _vars = vl
                        _cls += cl

                        if flag:
                            r = _v
                        else:
                            l = _v

                    # print(l, r)

                    if l[1] == 'f' or r[1] == 'f':
                        # one is a floating point.
                        for flag, v in enumerate([l, r]):
                            if v[1] == 't':
                                # if l is t, then convert to float
                                # find floating register that's free
                                i = 0
                                while f"$f{i}" in _vars.keys():
                                    i += 1
                                if i >= 32:
                                    raise Exception("Register overload")

                                _vars[f"$f{i}"] = _vars.pop(v)
                                _cls.append(f"mtc1 {v}, $f{i}")
                                _cls.append(f"cvt.s.w $f{i}, $f{i}")
                                if flag == 0:
                                    l = f"$f{i}"
                                else:
                                    r = f"$f{i}"
                        # floating ops
                        ops = {
                            "+": "add.s",
                            "-": "sub.s",
                            "*": "mul.s",
                            "/": 'div.s',
                        }

                        if o in ops.keys():
                            op = ops[o]
                            # print('f' in [l[1], r[1]])
                            _cls.append(f"{op} {l}, {l}, {r}  # {o}")
                        elif o in ['>', '>=', '<', '<=', '==', '!=']:
                            # print('equality')
                            # print(l, o, r)

                            comp = {
                                "<": "c.lt.s",
                                "<=": "c.le.s",
                                "==": "c.eq.s",
                                ">": "c.le.s",
                                ">=": "c.lt.s",
                                "!=": "c.eq.s"
                            }[o]

                            # if o in ['>', '>=', "!="]:
                            #     _cls.append(f"{comp} {r}, {l}")
                            # else:
                            _cls.append(f"{comp} {l}, {r}")

                            i = 0
                            while f"$t{i}" in _vars.keys():
                                i += 1
                            if i >= 10:
                                raise Exception("Register overload")
                            label = ".".join(scope + [f'c{condition_counter}'])
                            condition_counter += 1

                            _cls.append(f"li $t{i}, 0")
                            if o in ['>', '>=', "!="]:
                                _cls.append(f"bc1t {label}")
                            else:
                                _cls.append(f"bc1f {label}")

                            _cls.append(f"li $t{i}, 1")
                            _cls.append(f"{label}: ")

                            _vars[f"$t{i}"] = str(tr)
                            load_into = f"$t{i}"
                    else:
                        # integer ops
                        ops = {
                            "+": "add",
                            "-": "sub",
                            "*": "mul",
                            "/": 'div',
                            "%": 'rem',
                            "<": "slt",
                            ">": "sgt",
                            "==": "seq",
                            "!=": "sne",
                            ">=": "sge",
                            "&": "and",
                            "|": "or",
                            "^": "xor",
                        }
                        if o in ops.keys():
                            op = ops[o]
                            # print('f' in [l[1], r[1]])
                            _cls.append(f"{op} {l}, {l}, {r}  # {o}")
                        elif o == "<=":
                            _cls.append(f"sge {l}, {r}, {l}  # {o}")

                        load_into = None

                    _vars.pop(r)
                    if load_into is None:
                        load_into = l
                    else:
                        _vars.pop(l)
                    _vars[load_into] = str(tr)
                else:
                    raise NotImplementedError(f"Tree element of length: {len(tr)}")

                return _cls, _vars, load_into

            cl, vs, li = process_tree(body)

            # print(cl, vs, li, "---3---")

            assign_lines += cl
            if not li:
                raise Exception("No loading destination")
            if variables[var_name] == "float":
                if li[1] == "t":
                    # get an f register
                    fi = 0
                    while f"$f{fi}" in vs:
                        fi += 1

                    assign_lines.append(f"mtc1 {li}, $f{fi}")
                    assign_lines.append(f"cvt.s.w $f{fi}, $f{fi}")
                    # assign_lines.append(f"cvt.w.s {li}, {li}")  # convert back if we want to preserve
                    li = f"$f{fi}"

                assign_lines.append(f"s.s {li}, {var_name}")
            elif variables[var_name] == "int":
                if li[1] == "f":
                    # get a t register
                    ti = 0
                    while f"$t{ti}" in vs:
                        ti += 1

                    assign_lines.append(f"cvt.w.s {li}, {li}")
                    assign_lines.append(f"mfc1 $t{ti}, {li}")
                    # assign_lines.append(f"cvt.s.w {li}, {li}")  # convert back if we want to preserve
                    li = f"$t{ti}"

                assign_lines.append(f"sw {li}, {var_name}")

            code_lines += assign_lines
        elif statement_type == "Control Flow":
            # print(t)
            condition = t['condition']
            # print(condition)
            tks = expression_analyzer.tokenize_expression(condition[1:-1])
            # print(tks)

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
            data_type = t['data_type'].lower()
            write_lines = []

            if data_type == "variable":
                _s = scope[::]

                vn = ".".join(_s + [body])
                while vn not in variables.keys() and _s:
                    _s.pop(-1)
                    vn = ".".join(_s + [body])
                if not _s:
                    raise Exception(f"Variable {body} not found.")

                vn_d = variables[vn]
                if vn_d == "char":
                    write_lines.append(f"li $v0, 4")
                    write_lines.append(f"la $a0, {vn}")
                elif vn_d == "int":
                    write_lines.append(f"li $v0, 1")
                    write_lines.append(f"lw $a0, {vn}")
                elif vn_d == "float":
                    write_lines.append(f"li $v0, 2")
                    write_lines.append(f"l.s $f12, {vn}")
                write_lines.append("syscall")
            if data_type == "integer":
                # v0 = 1
                write_lines += [
                    "li $v0, 1",
                    f"li $a0, {body}",
                    "syscall"
                ]
            if data_type == "float":
                f_name = ".".join(["temp", *scope, 'f'])
                f_i = 0
                dl_names = [l.split(":")[0] for l in data_lines]
                while f"{f_name}{f_i}" in dl_names:
                    f_i += 1
                f_name = f"{f_name}{f_i}"

                data_lines.append(f"{f_name}: .float {body}")
                write_lines += [
                    "li $v0, 2",
                    f"l.s $f12, {f_name}",
                    "syscall"
                ]
                data_lines += dl_names
            if data_type == "char":
                # v0 = 4
                write_lines.append("li $v0, 4")
                cname = ".".join(["temp", *scope, 'c'])
                c_i = 0
                dl_names = [l.split(":")[0] for l in data_lines]
                while f"{cname}{c_i}" in dl_names:
                    c_i += 1
                cname = f"{cname}{c_i}"
                data_lines.append(f"{cname}: .asciiz {body}")
                write_lines.append(f"la $a0, {cname}")
                write_lines.append("syscall")

            code_lines += write_lines + [
                "li $v0, 11",
                "li $a0, 10",
                "syscall"
            ]
        code_lines.append("")

    if not global_level:
        return data_lines, code_lines
    return ["    .data"] + data_lines + ["    .text", "j global.main"] + \
           [c if c.strip().endswith(":") else "    " + c for c in code_lines]


if __name__ == '__main__':
    t1s = tokenize1(EXAMPLE_CODE_BLOCK)
    t2s = tokenize2(t1s)
    compiled = compile_snb(t2s)

    # print(*compiled, sep="\n")
    # exit(0)
    aligned = (align_comments(
        "\n".join([
            START_OF_BODY,
            # title_line("Compiled Code:"),
            # comment_block(EXAMPLE_CODE_BLOCK, dual_side=True),
            # DIV_LINE,
            *compiled,
            END_OF_BODY
        ]))).split("\n")
    aligned = "\n".join([a.rstrip() for a in aligned])

    with open("/home/kallatt/Desktop/can_delete.asm", 'w') as f:
        f.write(aligned)

    print('-' * 30, "Compiled")
    lines = aligned.split("\n")
    full = True
    if len(lines) < 60 or full:
        print(aligned)
    else:
        print(*lines[:30], "...", *lines[-26:-16], sep="\n")
    print('-' * 30, "Run")
    x = subprocess.Popen(
        ["java", "-jar", "/home/kallatt/Documents/mars.jar", 'nc', "/home/kallatt/Desktop/can_delete.asm"])
    res = x.communicate()
    # print(res)
