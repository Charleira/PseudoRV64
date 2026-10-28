import pytest
import ir as I
from executor import Interpreter, validate
from ast_nodes import *
from symbols import FunctionSymbol, SymbolKind


def program(instructions):
    span = SourceSpan(1, 1, 1, 2)
    fn = FunctionDecl(
        span=span,
        name="main",
        parameters=[],
        return_type=TypeName.INT,
        body=Block(span=span, statements=[]),
    )
    sym = FunctionSymbol("main", SymbolKind.FUNCTION, TypeName.INT, fn, ())
    r = I.VReg(sym, 0)
    return I.ProgramIR([I.FunctionIR(sym, instructions(r))])


def test_manual_ir():
    p = program(
        lambda r: [I.Li(r, (1 << 63) - 1), I.Addi(r, r, 1), I.PrintInt(r), I.Return(r)]
    )
    assert Interpreter().run(p).main_return == -(1 << 63)
    assert I.uses(p.functions[0].instructions[1]) == {
        p.functions[0].instructions[0].dst
    }


def test_bad_immediate():
    with pytest.raises(ValueError):
        validate(program(lambda r: [I.Addi(r, r, 2048), I.Return(r)]))


def test_uninitialized_read():
    with pytest.raises(RuntimeError, match="sem valor"):
        Interpreter().run(program(lambda r: [I.Return(r)]))


@pytest.mark.parametrize(
    "a,b,q,r",
    [(-7, 3, -2, -1), (7, -3, -2, 1), (-7, -3, 2, -1), (-(1 << 63), -1, -(1 << 63), 0)],
)
def test_signed_division(a, b, q, r):
    def instructions(v):
        w = I.VReg(v.owner, 1)
        out = I.VReg(v.owner, 2)
        return [
            I.Li(v, a),
            I.Li(w, b),
            I.Div(out, v, w),
            I.PrintInt(out),
            I.Rem(out, v, w),
            I.Return(out),
        ]

    result = Interpreter().run(program(instructions))
    assert (result.stdout, result.main_return) == (str(q), r)


def test_step_limit():
    def instructions(r):
        label = I.Label(r.owner, 0)
        return [I.LabelInstr(label), I.Jump(label)]

    with pytest.raises(RuntimeError, match="limite"):
        Interpreter().run(program(instructions), max_steps=10)


def test_ownership_and_missing_target():
    with pytest.raises(ValueError):
        validate(program(lambda r: [I.Move(r, I.VReg(object(), 0)), I.Return(r)]))
    with pytest.raises(ValueError):
        validate(program(lambda r: [I.Jump(I.Label(r.owner, 0))]))


def test_dump_preserves_string_pool_contents():
    import json

    text = 'ação "entre aspas"\n\tbarra: \\ e literal: \\n'
    ref = I.StringRef(0)
    ir = program(lambda r: [I.PrintString(ref), I.Li(r, 0), I.Return(r)])
    ir.strings[ref] = text

    dump = I.format_ir(ir)
    lines = dump.splitlines()
    assert lines[0] == ".strings"
    label, literal = lines[1].split(": ", 1)
    assert label == "str0"
    assert json.loads(literal) == text
    assert "\\n" in literal and "\\t" in literal
    assert "  print_string str0" in lines
    assert Interpreter().run(ir).stdout == text
