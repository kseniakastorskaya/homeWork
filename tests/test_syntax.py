import pytest
from lark import Lark, UnexpectedInput
from config_tool import GRAMMAR


def test_syntax_error():
    parser = Lark(GRAMMAR, parser="lalr")
    try:
        parser.parse("global = 10")
        assert False
    except UnexpectedInput:
        assert True
