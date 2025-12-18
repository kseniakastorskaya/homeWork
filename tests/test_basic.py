from config_tool import interp, ASTTransformer, GRAMMAR
from lark import Lark


def run(src):
    parser = Lark(GRAMMAR, parser="lalr")
    tree = parser.parse(src)
    ast = ASTTransformer().transform(tree)
    return interp(ast, {})


def test_add():
    assert run(".(2 3 +).") == [5]


def test_global():
    src = "global A = 5\n.(A 2 *)."
    assert run(src) == [10]
