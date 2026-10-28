import pytest
from Lexer import Lexer
from parser import Parser
from semantic import SemanticAnalyzer
from codegen import CodeGenerator
from executor import Interpreter, validate
from selector import Selector
from catalogue import catalogue
from patterns import *
from ast_nodes import *
import ir as I


def compile_source(source):
    p = Parser(Lexer(source).scan()).parse()
    SemanticAnalyzer().analyze(p)
    ir = CodeGenerator().generate(p)
    validate(ir)
    return ir


@pytest.mark.parametrize(
    "expr,expected",
    [
        ("2+3", 5),
        ("-7/3", -2),
        ("-7%3", -1),
        ("2*8", 16),
        ("3<=3", 1),
        ("3>=4", 0),
        ("true && !false", 1),
        ("false || true", 1),
    ],
)
def test_expressions(expr, expected):
    result = Interpreter().run(
        compile_source(f"int main() {{ print({expr}); return 0; }}")
    )
    assert (
        result.stdout
        == (
            {0: "false", 1: "true"}[expected]
            if any(s in expr for s in ["<", ">", "true", "false"])
            else str(expected)
        )
        + "\n"
    )


def test_short_circuit_and_order():
    source = (
        'bool f() { print("F"); return true; } int main() { bool x = true || '
        "f(); if (false && f()) { print(9); } print(x, f()); return 7; }"
    )
    r = Interpreter().run(compile_source(source))
    assert (r.stdout, r.main_return) == ("trueF\ntrue\n", 7)


def test_recursion_loop_shadowing():
    source = (
        "int f(int n) { if (n <= 1) { return 1; } return n * f(n-1); } int "
        "main() { int x=0; while (x<3) { int y=f(x); print(y); x=x+1; } { int"
        " x=9; print(x); } return x; }"
    )
    r = Interpreter().run(compile_source(source))
    assert (r.stdout, r.main_return) == ("1\n1\n2\n9\n", 3)


def test_synthetic_dp():
    s = SourceSpan(1, 1, 1, 2)
    node = IntLiteral(span=s, value=3)
    rules = [
        Rule("expensive", REG, Pattern(IntLiteral), 8, "x"),
        Rule("cheap", REG, Pattern(IntLiteral), 1, "x"),
    ]
    t = Selector(rules).analyze(node)
    assert t.lookup(node, REG).cost == 1
    assert t.lookup(node, COND) is None


@pytest.mark.parametrize("n", [-2049, -2048, 0, 2047, 2048])
def test_literal_classes(n):
    s = SourceSpan(1, 1, 1, 2)
    node = IntLiteral(span=s, value=abs(n))
    if n < 0:
        node = UnaryExpr(span=s, operator=UnaryOperator.NEGATE, operand=node)
    table = Selector(catalogue()).analyze(node)
    assert (table.lookup(node, IMM12) is not None) == (-2048 <= n <= 2047)


def test_direct_annotated_ast():
    from codegen import CodeGenerator
    from symbols import Scope
    from test_infrastructure import program

    p = program(lambda r: [])
    fn = p.functions[0].function.declaration
    fn.metadata["symbol"] = p.functions[0].function
    fn.body.metadata["scope"] = Scope(None)
    literal = IntLiteral(span=fn.span, value=42)
    literal.metadata["type"] = TypeName.INT
    fn.body.statements = [ReturnStmt(span=fn.span, value=literal)]
    ast = Program(span=fn.span, functions=[fn])
    assert Interpreter().run(CodeGenerator().generate(ast)).main_return == 42


@pytest.mark.parametrize(
    "expr,instruction",
    [("x+5", I.Addi), ("-2048+x", I.Addi), ("x*8", I.Slli), ("8*x", I.Slli)],
)
def test_instruction_selection(expr, instruction):
    ir = compile_source(
        f"int f(int x) {{ return {expr}; }} int main() {{ return f(3); }}"
    )
    assert any(isinstance(i, instruction) for i in ir.functions[0].instructions)


def test_direct_comparison_branch():
    ir = compile_source(
        "int f(int a,int b) { if (a<b) { return 1; } return 0; } int main() { return f(1,2); }"
    )
    assert any(isinstance(i, (I.Blt, I.Bge)) for i in ir.functions[0].instructions)
