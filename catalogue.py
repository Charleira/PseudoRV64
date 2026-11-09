"""Catálogo de regras do enunciado (Etapa 6), com Rule e Pattern."""

from ast_nodes import (
    IntLiteral,
    BoolLiteral,
    IdentifierExpr,
    UnaryExpr,
    UnaryOperator,
    BinaryExpr,
    BinaryOperator,
    CallExpr,
    TypeName,
)
from patterns import (
    Rule,
    Pattern,
    REG,
    IMM12,
    POW2,
    COND,
    EFFECT,
    Need,
    Args,
    imm12,
    pow2,
    neg_imm12,
    signed_literal,
)


# ---------------------------------------------------------------------------
# Predicados auxiliares. Todos tolerantes à falta de anotações: quando o tipo
# não é conhecido, a regra não é descartada (o frontend já validou os tipos).
# ---------------------------------------------------------------------------
def is_signed_literal(node):
    """Literal inteiro ou negação imediata dele. Atenção: 0 é literal válido."""
    return signed_literal(node) is not None


def _static_type(node):
    """Tipo MicroC anotado para o nó (símbolo ou anotação de tipo), se houver."""
    symbol = node.metadata.get("symbol")
    found = getattr(symbol, "type", None)
    if found is None:
        found = node.metadata.get("type")
    return found


def returns_value(node):
    """Chamada que produz valor: uma chamada void só oferece EFFECT."""
    return _static_type(node) is not TypeName.VOID


def returns_bool(node):
    """Chamada bool pode ser usada como COND."""
    found = _static_type(node)
    return found is None or found is TypeName.BOOL


def is_bool_identifier(node):
    """COND só se aplica a expressões bool."""
    found = _static_type(node)
    return found is None or found is TypeName.BOOL


def catalogue():
    """Codifique o catálogo do enunciado com Rule e Pattern."""
    rules = []

    # Literal inteiro com sinal (ou negação imediata) para REG, com Li. 1
    rules.append(
        Rule(
            name="int_reg",
            result=REG,
            pattern=Pattern(predicate=is_signed_literal),
            cost=1,
            action="literal_reg",
        )
    )

    # Literal bool para REG, com Li. 1
    rules.append(
        Rule(
            name="bool_reg",
            result=REG,
            pattern=Pattern(kind=BoolLiteral),
            cost=1,
            action="literal_reg",
        )
    )

    # Identificador para REG, reutilizando o VReg do símbolo. 0
    rules.append(
        Rule(
            name="identifier_reg",
            result=REG,
            pattern=Pattern(kind=IdentifierExpr),
            cost=0,
            action="identifier_reg",
        )
    )

    # Literal elegível para IMM12 ou POW2, sem instrução. 0
    rules.append(
        Rule(
            name="literal_imm12",
            result=IMM12,
            pattern=Pattern(predicate=imm12),
            cost=0,
            action="literal_imm12",
        )
    )
    rules.append(
        Rule(
            name="literal_pow2",
            result=POW2,
            pattern=Pattern(predicate=pow2),
            cost=0,
            action="literal_pow2",
        )
    )

    # Negação aritmética de REG para REG, com Neg. 1
    rules.append(
        Rule(
            name="negate_reg",
            result=REG,
            pattern=Pattern(
                kind=UnaryExpr,
                operator=UnaryOperator.NEGATE,
                children=(Need(REG),),
            ),
            cost=1,
            action="negate_reg",
        )
    )

    # Aritmética geral de dois REG para REG. 1
    for operator, name in [
        (BinaryOperator.ADD, "add_reg"),
        (BinaryOperator.SUBTRACT, "sub_reg"),
        (BinaryOperator.MULTIPLY, "mul_reg"),
        (BinaryOperator.DIVIDE, "div_reg"),
        (BinaryOperator.REMAINDER, "rem_reg"),
    ]:
        rules.append(
            Rule(
                name=name,
                result=REG,
                pattern=Pattern(
                    kind=BinaryExpr,
                    operator=operator,
                    children=(Need(REG), Need(REG)),
                ),
                cost=1,
                action=name,
            )
        )

    # Soma REG/IMM12 ou IMM12/REG, com Addi. 1
    rules.append(
        Rule(
            name="add_imm_right",
            result=REG,
            pattern=Pattern(
                kind=BinaryExpr,
                operator=BinaryOperator.ADD,
                children=(Need(REG), Need(IMM12)),
            ),
            cost=1,
            action="add_imm_right",
        )
    )
    rules.append(
        Rule(
            name="add_imm_left",
            result=REG,
            pattern=Pattern(
                kind=BinaryExpr,
                operator=BinaryOperator.ADD,
                children=(Need(IMM12), Need(REG)),
            ),
            cost=1,
            action="add_imm_left",
        )
    )

    # Subtração REG menos literal cujo oposto cabe no imediato, com Addi. 1
    # O literal é reconhecido diretamente (sem Need), só o x entra como REG.
    rules.append(
        Rule(
            name="sub_imm",
            result=REG,
            pattern=Pattern(
                kind=BinaryExpr,
                operator=BinaryOperator.SUBTRACT,
                children=(Need(REG), Pattern(predicate=neg_imm12)),
            ),
            cost=1,
            action="sub_imm",
        )
    )

    # Multiplicação REG/POW2 ou POW2/REG, com Slli. 1
    rules.append(
        Rule(
            name="mul_pow2_right",
            result=REG,
            pattern=Pattern(
                kind=BinaryExpr,
                operator=BinaryOperator.MULTIPLY,
                children=(Need(REG), Need(POW2)),
            ),
            cost=1,
            action="mul_pow2_right",
        )
    )
    rules.append(
        Rule(
            name="mul_pow2_left",
            result=REG,
            pattern=Pattern(
                kind=BinaryExpr,
                operator=BinaryOperator.MULTIPLY,
                children=(Need(POW2), Need(REG)),
            ),
            cost=1,
            action="mul_pow2_left",
        )
    )

    # Menor ou maior de dois REG para REG, com Slt. 1
    for operator, name in [
        (BinaryOperator.LESS, "less_reg"),
        (BinaryOperator.GREATER, "greater_reg"),
    ]:
        rules.append(
            Rule(
                name=name,
                result=REG,
                pattern=Pattern(
                    kind=BinaryExpr,
                    operator=operator,
                    children=(Need(REG), Need(REG)),
                ),
                cost=1,
                action=name,
            )
        )

    # Menor ou igual, maior ou igual para REG, com Slt e Seqz. 2
    for operator, name in [
        (BinaryOperator.LESS_EQUAL, "less_equal_reg"),
        (BinaryOperator.GREATER_EQUAL, "greater_equal_reg"),
    ]:
        rules.append(
            Rule(
                name=name,
                result=REG,
                pattern=Pattern(
                    kind=BinaryExpr,
                    operator=operator,
                    children=(Need(REG), Need(REG)),
                ),
                cost=2,
                action=name,
            )
        )

    # Igualdade/desigualdade para REG, com Xor e Seqz/Snez. 2
    for operator, name in [
        (BinaryOperator.EQUAL, "equal_reg"),
        (BinaryOperator.NOT_EQUAL, "not_equal_reg"),
    ]:
        rules.append(
            Rule(
                name=name,
                result=REG,
                pattern=Pattern(
                    kind=BinaryExpr,
                    operator=operator,
                    children=(Need(REG), Need(REG)),
                ),
                cost=2,
                action=name,
            )
        )

    # Comparação de dois REG para COND, branch direto e Jump. 2
    for operator, name in [
        (BinaryOperator.LESS, "less_cond"),
        (BinaryOperator.LESS_EQUAL, "less_equal_cond"),
        (BinaryOperator.GREATER, "greater_cond"),
        (BinaryOperator.GREATER_EQUAL, "greater_equal_cond"),
        (BinaryOperator.EQUAL, "equal_cond"),
        (BinaryOperator.NOT_EQUAL, "not_equal_cond"),
    ]:
        rules.append(
            Rule(
                name=name,
                result=COND,
                pattern=Pattern(
                    kind=BinaryExpr,
                    operator=operator,
                    children=(Need(REG), Need(REG)),
                ),
                cost=2,
                action=name,
            )
        )

    # Negação lógica de REG para REG, com Seqz. 1
    rules.append(
        Rule(
            name="not_reg",
            result=REG,
            pattern=Pattern(
                kind=UnaryExpr,
                operator=UnaryOperator.NOT,
                children=(Need(REG),),
            ),
            cost=1,
            action="not_reg",
        )
    )

    # Negação lógica de COND para COND, invertendo destinos. 0
    rules.append(
        Rule(
            name="not_cond",
            result=COND,
            pattern=Pattern(
                kind=UnaryExpr,
                operator=UnaryOperator.NOT,
                children=(Need(COND),),
            ),
            cost=0,
            action="not_cond",
        )
    )

    # &&/|| de dois COND para COND. 0
    for operator, name in [
        (BinaryOperator.LOGICAL_AND, "and_cond"),
        (BinaryOperator.LOGICAL_OR, "or_cond"),
    ]:
        rules.append(
            Rule(
                name=name,
                result=COND,
                pattern=Pattern(
                    kind=BinaryExpr,
                    operator=operator,
                    children=(Need(COND), Need(COND)),
                ),
                cost=0,
                action=name,
            )
        )

    # &&/|| de dois COND para REG, com duas Li e um Jump. 3
    for operator, name in [
        (BinaryOperator.LOGICAL_AND, "and_reg"),
        (BinaryOperator.LOGICAL_OR, "or_reg"),
    ]:
        rules.append(
            Rule(
                name=name,
                result=REG,
                pattern=Pattern(
                    kind=BinaryExpr,
                    operator=operator,
                    children=(Need(COND), Need(COND)),
                ),
                cost=3,
                action=name,
            )
        )

    # Literal bool para COND, com Jump. 1
    rules.append(
        Rule(
            name="bool_cond",
            result=COND,
            pattern=Pattern(kind=BoolLiteral),
            cost=1,
            action="bool_cond",
        )
    )

    # Identificador bool para COND, com branch e Jump. 2
    rules.append(
        Rule(
            name="identifier_cond",
            result=COND,
            pattern=Pattern(kind=IdentifierExpr, predicate=is_bool_identifier),
            cost=2,
            action="identifier_cond",
        )
    )

    # Chamada com argumentos REG para REG (se produz valor) ou EFFECT, com Call. 1
    rules.append(
        Rule(
            name="call_reg",
            result=REG,
            pattern=Pattern(
                kind=CallExpr, children=(Args(REG),), predicate=returns_value
            ),
            cost=1,
            action="call_reg",
        )
    )
    rules.append(
        Rule(
            name="call_effect",
            result=EFFECT,
            pattern=Pattern(kind=CallExpr, children=(Args(REG),)),
            cost=1,
            action="call_effect",
        )
    )

    # Chamada bool com argumentos REG para COND, com chamada e desvios. 3
    rules.append(
        Rule(
            name="call_cond",
            result=COND,
            pattern=Pattern(
                kind=CallExpr, children=(Args(REG),), predicate=returns_bool
            ),
            cost=3,
            action="call_cond",
        )
    )

    return rules