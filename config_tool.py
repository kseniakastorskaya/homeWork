import sys
import argparse
import yaml
from lark import Lark, Transformer, UnexpectedInput, Tree

# ================== GRAMMAR ==================

GRAMMAR = r"""
start: statement+

statement: global_decl
         | value

global_decl: "global" NAME "=" value

?value: NUMBER           -> number
      | STRING           -> string
      | dict
      | rpn_expr
      | NAME             -> reference

dict: "([" pair ("," pair)* ","? "])"
pair: NAME ":" value

rpn_expr: ".(" rpn_item+ ")."
rpn_item: NUMBER | NAME | OP | FUNC

OP: "+" | "-" | "*"
FUNC: "mod"

NAME: /[_A-Z][_a-zA-Z0-9]*/
STRING: /'[^']*'/
NUMBER: /[+-]?\d+/

COMMENT: "=begin" /(.|\n)*?/ "=end"

%ignore COMMENT
%ignore /[ \t\r\n]+/
"""

# ================== TRANSFORMER ==================


class ASTTransformer(Transformer):
    def __init__(self):
        self.globals = {}

    def start(self, items):
        return items

    def statement(self, items):
        return items[0]

    def global_decl(self, items):
        name = str(items[0])
        value = items[1]
        self.globals[name] = value
        return ("global", name, value)

    def number(self, items):
        return int(items[0])

    def string(self, items):
        return items[0][1:-1]

    def reference(self, items):
        return ("ref", str(items[0]))

    def pair(self, items):
        return (str(items[0]), items[1])

    def dict(self, items):
        return dict(items)

    def rpn_expr(self, items):
        return ("rpn", items)

    def rpn_item(self, items):
        return items[0]


# ================== INTERPRETER ==================


def interp(tree, env):
    # 🔹 FIX 1: unwrap Tree
    if isinstance(tree, Tree):
        if len(tree.children) == 1:
            return interp(tree.children[0], env)
        return interp(tree.children, env)

    if isinstance(tree, int):
        return tree

    if isinstance(tree, str):
        return tree

    if isinstance(tree, dict):
        return {k: interp(v, env) for k, v in tree.items()}

    if isinstance(tree, list):
        result = []
        for item in tree:
            res = interp(item, env)
            if res is not None:
                result.append(res)
        return result

    if isinstance(tree, tuple):
        tag = tree[0]

        if tag == "global":
            _, name, value = tree
            env[name] = interp(value, env)
            return None

        if tag == "ref":
            name = tree[1]
            if name not in env:
                raise ValueError(f"Unknown identifier: {name}")
            return env[name]

        if tag == "rpn":
            tokens = tree[1]
            stack = []

            for tok in tokens:
                if isinstance(tok, int):
                    stack.append(tok)
                elif isinstance(tok, str) and tok in env:
                    stack.append(env[tok])
                elif tok in {"+", "-", "*", "mod"}:
                    b = stack.pop()
                    a = stack.pop()
                    if tok == "+":
                        stack.append(a + b)
                    elif tok == "-":
                        stack.append(a - b)
                    elif tok == "*":
                        stack.append(a * b)
                    elif tok == "mod":
                        stack.append(a % b)
                else:
                    raise ValueError(f"Unknown RPN token: {tok}")

            if len(stack) != 1:
                raise ValueError("Invalid RPN expression")

            return stack[0]

    raise ValueError(f"Unsupported AST node: {tree}")


# ================== CLI ==================


def main():
    parser = argparse.ArgumentParser(
        description="Educational configuration language → YAML"
    )
    parser.add_argument("--input", required=True, help="Input config file")
    parser.add_argument("--output", required=True, help="Output YAML file")
    parser.add_argument("--test", action="store_true", help="Debug output")

    args = parser.parse_args()

    try:
        with open(args.input, encoding="utf-8") as f:
            text = f.read()

        parser_lark = Lark(GRAMMAR, parser="lalr")
        tree = parser_lark.parse(text)

        transformer = ASTTransformer()
        ast = transformer.transform(tree)

        env = {}
        result = interp(ast, env)

        with open(args.output, "w", encoding="utf-8") as f:
            yaml.safe_dump(result, f, allow_unicode=True)

        if args.test:
            print("Globals:")
            print(env)
            print("Result:")
            print(result)

        print(f"✔ YAML written to {args.output}")

    except UnexpectedInput as e:
        print("❌ Syntax error:")
        print(e)
        sys.exit(1)

    except Exception as e:
        print("❌ Error:")
        print(e)
        sys.exit(1)


# ================== ENTRY ==================

if __name__ == "__main__":
    main()
