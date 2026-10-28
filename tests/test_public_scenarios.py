"""Casos públicos de seleção e comportamento, com expectativas explícitas."""

import pytest

from ast_nodes import BinaryExpr, BinaryOperator, IntLiteral, SourceSpan
from catalogue import catalogue
from executor import Interpreter
from patterns import COND, IMM12, REG, Need, Pattern, Rule
from selector import Selector
from test_codegen import compile_source


def execute(source):
    return Interpreter().run(compile_source(source))


@pytest.mark.parametrize(
    "operator,expected",
    [
        ("<", (True, False)),
        ("<=", (True, True)),
        (">", (False, False)),
        (">=", (False, True)),
        ("==", (False, True)),
        ("!=", (True, False)),
    ],
)
@pytest.mark.parametrize("pair", [0, 1], ids=["menor", "igual"])
def test_comparison_value_and_condition(operator, expected, pair):
    a, b = [(2, 5), (5, 5)][pair]
    source = f"""
        bool compare(int a, int b) {{ return a {operator} b; }}
        int main() {{
            bool value = compare({a}, {b});
            print(value);
            if ({a} {operator} {b}) {{ return 1; }}
            return 0;
        }}
    """
    result = execute(source)
    value = expected[pair]
    assert (result.stdout, result.main_return) == (
        "true\n" if value else "false\n",
        int(value),
    )


@pytest.mark.parametrize(
    "expression,output",
    [
        ("false && mark()", "false\n"),
        ("true || mark()", "true\n"),
        ("true && mark()", "M\ntrue\n"),
        ("false || mark()", "M\ntrue\n"),
    ],
)
@pytest.mark.parametrize("context", ["return", "argument"])
def test_effect_contexts_public(expression, output, context):
    if context == "return":
        helper = f"bool value() {{ return {expression}; }}"
        body = "print(value());"
    else:
        helper = "void show(bool value) { print(value); }"
        body = f"show({expression});"
    source = (
        'bool mark() { print("M"); return true; }'
        + helper
        + "int main() {"
        + body
        + "return 0; }"
    )
    assert execute(source).stdout == output


@pytest.mark.parametrize("arity", [0, 9])
def test_call_parameter_indices_public(arity):
    parameters = ",".join(f"int p{i}" for i in range(arity))
    arguments = ",".join(str(i + 1) for i in range(arity))
    value = "p0 - p8" if arity else "42"
    source = (
        f"int f({parameters}) {{ return {value}; }}"
        f"int main() {{ return f({arguments}); }}"
    )
    assert execute(source).main_return == (-8 if arity else 42)


def test_parameter_order_with_observable_arguments():
    source = """
        int mark(int x) { print(x); return x; }
        int difference(int a, int b) { return a - b; }
        int main() { return difference(mark(9), mark(2)); }
    """
    result = execute(source)
    assert (result.stdout, result.main_return) == ("9\n2\n", 7)


@pytest.mark.parametrize(
    "body,expected",
    [
        ("return;", ""),
        ("", ""),
        ('print("fim");', "fim\n"),
    ],
)
def test_void_exit_and_discarded_call(body, expected):
    source = (
        f"void done() {{ {body} }}"
        "int value() { return 7; }"
        "int main() { done(); value(); return 3; }"
    )
    result = execute(source)
    assert (result.stdout, result.main_return) == (expected, 3)


@pytest.mark.parametrize(
    "source,expected",
    [
        ("int main() { int x; if (true) { x=7; } else { return 9; } return x; }", 7),
        ("int main() { int x=5; while (false) { x=9; } return x; }", 5),
        (
            "int main() { int x=0; while (x<5) { x=x+1; if (x==3) { return x; } } return 9; }",
            3,
        ),
        ("int main() { int x=1; { int x=8; print(x); } { x=x+2; } return x; }", 3),
    ],
)
def test_statement_paths_public(source, expected):
    result = execute(source)
    assert result.main_return == expected
    assert result.stdout == ("8\n" if "int x=8" in source else "")


@pytest.mark.parametrize(
    "items,expected",
    [
        ('"a" "b", "", true, -2', "abtrue-2\n"),
        ('"linha\\n", "\\t", false', "linha\n\tfalse\n"),
    ],
)
def test_print_decoded_strings_and_final_newline(items, expected):
    assert execute(f"int main() {{ print({items}); return 0; }}").stdout == expected


@pytest.mark.parametrize(
    "expression,expected",
    [
        ("9223372036854775807 + 1", -9223372036854775808),
        ("(-9223372036854775807 - 1) / -1", -9223372036854775808),
        ("-7 / 3", -2),
        ("-7 % 3", -1),
    ],
)
def test_integer_semantics_public(expression, expected):
    assert execute(f"int main() {{ return {expression}; }}").main_return == expected


@pytest.mark.parametrize("expression,cost", [("x+5", 1), ("x+2048", 2), ("(x+5)*8", 2)])
def test_catalogue_costs_public(expression, cost):
    # A expressão é construída diretamente, sem depender do parser do grupo.
    from ast_nodes import IdentifierExpr
    from symbols import Symbol, SymbolKind
    from ast_nodes import TypeName, VarDecl

    span = SourceSpan(1, 1, 1, 2)
    x = IdentifierExpr(span=span, name="x")
    declaration = VarDecl(span=span, type=TypeName.INT, name="x", initializer=None)
    symbol = Symbol("x", SymbolKind.VARIABLE, TypeName.INT, declaration)
    declaration.metadata["symbol"] = symbol
    x.metadata.update(type=TypeName.INT, symbol=symbol)
    constant = IntLiteral(span=span, value=2048 if expression == "x+2048" else 5)
    node = BinaryExpr(span=span, operator=BinaryOperator.ADD, left=x, right=constant)
    if expression.startswith("("):
        node = BinaryExpr(
            span=span,
            operator=BinaryOperator.MULTIPLY,
            left=node,
            right=IntLiteral(span=span, value=8),
        )
    assert Selector(catalogue()).analyze(node).lookup(node, REG).cost == cost


@pytest.mark.parametrize(
    "covered", [False, True], ids=["filho-sem-classe", "filho-com-classe"]
)
def test_dp_requires_child_class(covered):
    span = SourceSpan(1, 1, 1, 2)
    leaf = IntLiteral(span=span, value=3)
    node = BinaryExpr(
        span=span,
        operator=BinaryOperator.ADD,
        left=leaf,
        right=IntLiteral(span=span, value=5),
    )
    rules = [
        Rule("number", REG, Pattern(IntLiteral), 1, "number"),
        Rule(
            "immediate_add",
            REG,
            Pattern(BinaryExpr, BinaryOperator.ADD, (Need(REG), Need(IMM12))),
            1,
            "immediate_add",
        ),
    ]
    if covered:
        rules.append(Rule("immediate", IMM12, Pattern(IntLiteral), 0, "immediate"))
    table = Selector(rules).analyze(node)
    choice = table.lookup(node, REG)
    if covered:
        assert choice.cost == 2
        assert choice.subproblems == ((leaf, REG), (node.right, IMM12))
    else:
        assert choice is None
    assert table.lookup(node, COND) is None


def test_dp_equal_cost_choices_are_stable():
    node = IntLiteral(span=SourceSpan(1, 1, 1, 2), value=5)
    rules = [Rule(name, REG, Pattern(IntLiteral), 1, name) for name in ("a", "b")]
    first = Selector(rules).analyze(node).lookup(node, REG)
    second = Selector(rules).analyze(node).lookup(node, REG)
    assert first.cost == second.cost == 1
    assert first.rule.name == second.rule.name


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("selecao.mc", "12\n"),
        ("curto_circuito.mc", "M\ntrue\n"),
    ],
)
def test_handout_examples(filename, expected):
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "examples" / filename).read_text()
    result = execute(source)
    assert (result.stdout, result.main_return) == (expected, 0)


def test_print_final_newline_uses_shared_string_pool():
    import ir as I

    source = r"""
        void show() { print("x"); }
        int main() {
            print(1, true, "");
            show();
            print("\n");
            return 0;
        }
    """
    program = compile_source(source)
    newline_refs = {ref for ref, value in program.strings.items() if value == "\n"}
    assert len(newline_refs) == 1
    newline_ref = next(iter(newline_refs))
    newline_instructions = [
        instruction
        for function in program.functions
        for instruction in function.instructions
        if isinstance(instruction, I.PrintString) and instruction.string == newline_ref
    ]
    # Três quebras finais e uma quebra escrita como item explícito.
    assert len(newline_instructions) == 4
    assert all(not I.uses(i) and not I.defs(i) for i in newline_instructions)
    result = Interpreter().run(program)
    assert (result.stdout, result.main_return) == ("1true\nx\n\n\n", 0)


@pytest.mark.parametrize("constant", [-2049, -2048, -2047, -1, 0, 2047, 2048, 2049])
def test_subtraction_literal_selection(constant):
    import ir as I

    source = (
        f"int difference(int x) {{ return x - ({constant}); }}"
        "int main() { return difference(7); }"
    )
    program = compile_source(source)
    instructions = program.functions[0].instructions
    if -2048 <= -constant <= 2047:
        assert any(isinstance(i, I.Addi) and i.imm == -constant for i in instructions)
        assert not any(isinstance(i, I.Sub) for i in instructions)
    else:
        assert any(isinstance(i, I.Sub) for i in instructions)
        assert not any(isinstance(i, I.Addi) for i in instructions)
    assert Interpreter().run(program).main_return == 7 - constant


def test_subtraction_literal_on_left_stays_general():
    import ir as I

    program = compile_source(
        "int difference(int x) { return 2048 - x; }"
        "int main() { return difference(7); }"
    )
    assert any(isinstance(i, I.Sub) for i in program.functions[0].instructions)
    assert Interpreter().run(program).main_return == 2041


def test_subtraction_immediate_evaluates_call_once():
    source = """
        int mark() { print("M"); return 7; }
        int main() { return mark() - 2048; }
    """
    result = execute(source)
    assert (result.stdout, result.main_return) == ("M\n", -2041)
