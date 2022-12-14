import re


def tokenize_expression(expr):
    pattern = re.compile(r"\b")
    tokens = re.split(pattern, expr)
    operators = set(r"+-*/&|!^%()=<>") | {f"{x}=" for x in "><=!"}

    while '.' in tokens:
        i = tokens.index('.')
        x = tokens.pop(i-1)
        y = tokens.pop(i)
        tokens[i-1] = f'{x}.{y}'

    new_tokens = []
    for token in tokens:
        no_space = re.sub(r"\s", "", token)
        if set(no_space).issubset(operators):
            new_tokens += list(no_space)
        elif re.match(r"([a-zA-Z_][a-zA-Z_0-9]*)", token):
            new_tokens.append({"token": token, "type": "variable"})
        elif re.match(r'"(^"|\\")"', token):
            new_tokens.append({"token": token, "type": "string literal"})
        elif re.match(r'([1-9][0-9]*|0)\.[0-9]+', token):
            new_tokens.append({"token": token, "type": "float literal"})
        elif re.match(r'[1-9][0-9]*|0', token):
            new_tokens.append({"token": token, "type": "int literal"})
    tokens = new_tokens

    def match_parentheses(lst):
        if "(" not in lst:
            return lst
        ts = []
        open_indexes = []
        for i, token in enumerate(lst):
            if token == "(":
                open_indexes.append(i)
            elif token == ")":
                o = open_indexes.pop(-1)
                c = i
                l = lst[o + 1: c]
                ln = match_parentheses(l)
                ts = ts[:-len(l)]
                ts.append(ln)
            else:
                ts.append(token)
        return ts

    def order_of_operations(lst):
        if isinstance(lst, dict) and set(lst.keys()) == {"token", "type"}:
            return lst
        elif len(lst) == 1:
            return lst
        elif len(lst) == 3:
            expr1, op, expr2 = lst
            e1n = order_of_operations(expr1)
            e2n = order_of_operations(expr2)
            return [e1n, op, e2n]
        elif len(lst) == 4:
            expr1, op1, op2, expr2 = lst
            e1n = order_of_operations(expr1)
            e2n = order_of_operations(expr2)
            return [e1n, op1+op2, e2n]
        else:
            op_priority = {
                "<": 0,
                ">": 0,
                "<=": 0,
                ">=": 0,
                "!=": 0,
                "==": 0,
                "+": 1,
                "-": 1,
                "*": 2,
                "/": 2,
                "%": 3,
                "&": 4,
                "|": 4,
                "^": 4,
                "!": 5,
            }
            ops = list(op_priority.keys())

            priority_ops = [[], [], [], [], [], []]

            for i, tkn in enumerate(lst):
                # print(tkn)
                if tkn in ops:
                    priority_ops[op_priority[tkn]].append(i)

            ops_in_order = sum(reversed(priority_ops), [])

            while ops_in_order:
                op_i = ops_in_order.pop(0)
                op = lst[op_i]
                shift_amount = 2
                if op == "!":
                    nt = (lst.pop(op_i+1), "!")
                    lst[op_i] = nt
                    shift_amount = 1
                else:
                    nt = [lst.pop(op_i-1), op, lst.pop(op_i)]
                    lst[op_i-1] = nt

                # shift op indices
                ops_in_order = [
                    e if e < op_i else e - shift_amount for e in ops_in_order
                ]

        return lst

    matched = match_parentheses(tokens)
    # print(matched)
    postfix_notation = order_of_operations(matched)
    # print(postfix_notation)
    def flatten(lst):
        new_lst = []
        for l in lst:
            if isinstance(l, list):
                new_lst += flatten(l)
            else:
                new_lst.append(l)
        return new_lst

    # steps = flatten(postfix_notation)
    return postfix_notation


if __name__ == '__main__':
    # expression = r"(foo + bar) % 2"
    # expression = r"(foo * (bar & baz)) < 6"
    expression = r" (x * (x < y)) + (y * (x >= y))"
    tokens = tokenize_expression(expression)
    # print(tokens)
