import sys
import yaml
from lark import Lark, Transformer, v_args, UnexpectedInput

GRAMMAR = r"""
?start: config

config: (global_decl)* expr*

global_decl: "global" IDENT "=" value

?expr: dict
     | list

dict: "([" pair_list "])"
list: "[" value_list "]"

pair_list: (pair ("," pair)* (","?) )?
pair: IDENT ":" value

value_list: (value ("," value)* (","?) )?

?value: NUMBER           -> num
      | STRING           -> string
      | IDENT            -> ident_value
      | dict
      | list
      | expr_const

expr_const: ".(" rpn_list ")."
rpn_list: (IDENT | NUMBER | OP | FUNC)+

OP: "+"|"-"|"*"|"/"
FUNC: "mod"

IDENT: /[A-Za-z_][A-Za-z0-9_]*/
STRING: /'[^']*'/
NUMBER: /-?\d+/

%import common.WS
%ignore WS
"""

# ------------------ Transformer ------------------


@v_args(inline=True)
class ConfigTransformer(Transformer):
    def __init__(self):
        super().__init__()
        self.globals = {}

    # ---------- Globals ----------
    def global_decl(self, name, value):
        self.globals[str(name)] = value
        return ("global", str(name), value)

    # ---------- Values ----------
    def num(self, n):
        return int(n)

    def string(self, s):
        return s[1:-1]

    def ident_value(self, name):
        key = str(name)
        if key in self.globals:
            return self.globals[key]
        else:
            raise ValueError(f"Unknown identifier: {key}")

    # ---------- RPN ----------
    def expr_const(self, rpn_tree):
        # rpn_tree может быть Tree или list
        tokens = getattr(rpn_tree, "children", rpn_tree)
        stack = []
        for tok in tokens:
            tok_str = str(tok)
            if isinstance(tok, int):
                stack.append(tok)
            elif tok_str in self.globals:
                stack.append(self.globals[tok_str])
            elif tok_str.isdigit() or (
                tok_str.startswith("-") and tok_str[1:].isdigit()
            ):
                stack.append(int(tok_str))
            elif tok_str in ["+", "-", "*", "/", "mod"]:
                b = stack.pop()
                a = stack.pop()
                if tok_str == "+":
                    stack.append(a + b)
                elif tok_str == "-":
                    stack.append(a - b)
                elif tok_str == "*":
                    stack.append(a * b)
                elif tok_str == "/":
                    stack.append(a // b)
                elif tok_str == "mod":
                    stack.append(a % b)
            else:
                raise ValueError(f"Unknown token in RPN: {tok_str}")
        if len(stack) != 1:
            raise ValueError("Invalid RPN expression")
        return stack[0]

    # ---------- Structures ----------
    def pair(self, key, value):
        return (str(key), value)

    def pair_list(self, *pairs):
        d = {}
        for p in pairs:
            if isinstance(p, tuple) and len(p) == 2:
                d[p[0]] = p[1]
        return d

    def value_list(self, *vals):
        return list(vals)

    def dict(self, items):
        if isinstance(items, dict):
            return items
        elif isinstance(items, list):
            d = {}
            for x in items:
                if isinstance(x, dict):
                    d.update(x)
            return d
        return {}

    def list(self, items):
        if isinstance(items, list):
            return items
        return [items]

    # ---------- Root ----------
    def config(self, *items):
        # возвращаем только выражения (не глобалы)
        return [i for i in items if not (isinstance(i, tuple) and i[0] == "global")]


# ------------------ CLI functions ------------------


def assemble(input_path, output_path, test_mode=False):
    parser = Lark(GRAMMAR, parser="lalr")
    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()
    try:
        tree = parser.parse(text)
        trans = ConfigTransformer()
        statements = trans.transform(tree)

        # Save to YAML
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                {"globals": trans.globals, "statements": statements},
                f,
                sort_keys=False,
                allow_unicode=True,
            )

        if test_mode:
            print("Globals:")
            for k, v in trans.globals.items():
                print(f"  {k} = {v}")
            print("Statements:")
            print(statements)

        print(f"Wrote IR to {output_path}")

    except UnexpectedInput as e:
        print(f"Syntax error in {input_path}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


# ------------------ Main ------------------


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Config language tool: parse -> IR -> YAML"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_assemble = sub.add_parser("assemble", help="Assemble source to IR (YAML)")
    p_assemble.add_argument("infile")
    p_assemble.add_argument("outfile")
    p_assemble.add_argument("--test", action="store_true")

    args = parser.parse_args()

    if args.cmd == "assemble":
        assemble(args.infile, args.outfile, args.test)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
