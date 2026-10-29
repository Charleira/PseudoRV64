from __future__ import annotations

from ast_nodes import (
    Assignment,
    BinaryExpr,
    BinaryOperator as B,
    Block,
    BoolLiteral,
    CallExpr,
    CallStmt,
    Expr,
    FunctionDecl,
    IdentifierExpr,
    IfStmt,
    IntLiteral,
    Node,
    PrintStmt,
    Program,
    ReturnStmt,
    StringLiteral,
    TypeName,
    UnaryExpr,
    UnaryOperator as U,
    VarDecl,
    WhileStmt,
)
from semantic_errors import SemanticDiagnostic, SemanticError, SemanticErrorKind

INT_MAX = 2**63 - 1

_ARITHMETIC = {B.ADD, B.SUBTRACT, B.MULTIPLY, B.DIVIDE, B.REMAINDER}
_RELATIONAL = {B.LESS, B.LESS_EQUAL, B.GREATER, B.GREATER_EQUAL}
_EQUALITY = {B.EQUAL, B.NOT_EQUAL}
_LOGICAL = {B.LOGICAL_AND, B.LOGICAL_OR}

_UNKNOWN = object()  # estado interno; nunca vai para metadata


def check_types(program: Program) -> None:
    """Determine tipos de expressões e valide seus contextos."""
    checker = _TypeChecker()
    for function in program.functions:
        checker.visit_function(function)
    if checker.diagnostics:
        raise SemanticError(checker.diagnostics)


class _TypeChecker:
    def __init__(self) -> None:
        self.diagnostics: list[SemanticDiagnostic] = []
        self.return_type: object = _UNKNOWN

    def error(self, kind: SemanticErrorKind, node: Node, message: str) -> None:
        self.diagnostics.append(SemanticDiagnostic(kind, message, node.span))

    # ------------------------------------------------------------------
    def visit_function(self, function: FunctionDecl) -> None:
        self.return_type = function.return_type
        for parameter in function.parameters:
            if parameter.type is TypeName.VOID:
                self.error(
                    SemanticErrorKind.VOID_PARAMETER,
                    parameter,
                    f"parâmetro '{parameter.name}' não pode ser void",
                )
        for statement in function.body.statements:
            self.statement(statement)

    # ---------------- comandos ----------------
    def statement(self, node: Node) -> None:
        if isinstance(node, Block):
            for inner in node.statements:
                self.statement(inner)
        elif isinstance(node, VarDecl):
            if node.type is TypeName.VOID:
                self.error(
                    SemanticErrorKind.VOID_VARIABLE,
                    node,
                    f"variável '{node.name}' não pode ser void",
                )
            if node.initializer is not None:
                found = self.value(node.initializer)
                if (
                    node.type is not TypeName.VOID
                    and found is not _UNKNOWN
                    and found is not node.type
                ):
                    self.error(
                        SemanticErrorKind.INITIALIZER_TYPE_MISMATCH,
                        node.initializer,
                        f"inicializador {found.value} incompatível com "
                        f"{node.type.value}",
                    )
        elif isinstance(node, Assignment):
            target = self.value(node.target)
            found = self.value(node.value)
            if target is not _UNKNOWN and found is not _UNKNOWN and found is not target:
                self.error(
                    SemanticErrorKind.ASSIGNMENT_TYPE_MISMATCH,
                    node.value,
                    f"atribuição de {found.value} a variável {target.value}",
                )
        elif isinstance(node, CallStmt):
            self.expression(node.call)  # int/bool/void permitidos como comando
        elif isinstance(node, (IfStmt, WhileStmt)):
            self.condition(node.condition)
            if isinstance(node, IfStmt):
                self.statement(node.then_block)
                if node.else_block is not None:
                    self.statement(node.else_block)
            else:
                self.statement(node.body)
        elif isinstance(node, ReturnStmt):
            self.return_statement(node)
        elif isinstance(node, PrintStmt):
            for item in node.items:
                if not isinstance(item, StringLiteral):  # string: sem tipo
                    self.value(item)

    def condition(self, expr: Expr) -> None:
        found = self.value(expr)
        if found is not _UNKNOWN and found is not TypeName.BOOL:
            self.error(
                SemanticErrorKind.CONDITION_TYPE_MISMATCH,
                expr,
                f"condição deve ser bool, mas é {found.value}",
            )

    def return_statement(self, node: ReturnStmt) -> None:
        expected = self.return_type
        if node.value is None:
            if expected is not TypeName.VOID:
                self.error(
                    SemanticErrorKind.RETURN_MISMATCH,
                    node,
                    "return sem valor em função não-void",
                )
            return
        found = self.value(node.value)
        if expected is TypeName.VOID:
            self.error(
                SemanticErrorKind.RETURN_MISMATCH,
                node.value,
                "return com valor em função void",
            )
        elif found is not _UNKNOWN and found is not expected:
            self.error(
                SemanticErrorKind.RETURN_MISMATCH,
                node.value,
                f"retorno {found.value}, esperado {expected.value}",
            )

    # ---------------- expressões ----------------
    def value(self, expr: Expr):
        """Expressão usada como valor: void não é permitido."""
        found = self.expression(expr)
        if found is TypeName.VOID:
            self.error(
                SemanticErrorKind.VOID_VALUE_USED,
                expr,
                "chamada void não pode ser usada como valor",
            )
            return _UNKNOWN
        return found

    def annotate(self, expr: Expr, found):
        if found is not _UNKNOWN:
            expr.metadata["type"] = found
        return found

    def expression(self, expr: Expr):
        if isinstance(expr, IntLiteral):
            if not 0 <= expr.value <= INT_MAX:
                self.error(
                    SemanticErrorKind.INTEGER_LITERAL_OUT_OF_RANGE,
                    expr,
                    "literal inteiro fora do intervalo [0, 2^63-1]",
                )
            return self.annotate(expr, TypeName.INT)
        if isinstance(expr, BoolLiteral):
            return self.annotate(expr, TypeName.BOOL)
        if isinstance(expr, IdentifierExpr):
            symbol = expr.metadata.get("symbol")
            return self.annotate(expr, symbol.type) if symbol else _UNKNOWN
        if isinstance(expr, UnaryExpr):
            return self.unary(expr)
        if isinstance(expr, BinaryExpr):
            return self.binary(expr)
        if isinstance(expr, CallExpr):
            return self.call(expr)
        return _UNKNOWN

    def unary(self, expr: UnaryExpr):
        operand = self.value(expr.operand)
        needed = TypeName.INT if expr.operator is U.NEGATE else TypeName.BOOL
        if operand is _UNKNOWN:
            return self.annotate(expr, needed)  # sem diagnóstico em cascata
        if operand is not needed:
            self.error(
                SemanticErrorKind.INVALID_UNARY_OPERAND,
                expr,
                f"operador '{expr.operator.value}' não aceita {operand.value}",
            )
            return _UNKNOWN
        return self.annotate(expr, needed)

    def binary(self, expr: BinaryExpr):
        left = self.value(expr.left)  # visita sempre os dois filhos
        right = self.value(expr.right)
        op = expr.operator
        if op in _ARITHMETIC:
            result, ok = TypeName.INT, (left, right) == (TypeName.INT,) * 2
        elif op in _RELATIONAL:
            result, ok = TypeName.BOOL, (left, right) == (TypeName.INT,) * 2
        elif op in _EQUALITY:
            result, ok = TypeName.BOOL, left is right
        else:
            result, ok = TypeName.BOOL, (left, right) == (TypeName.BOOL,) * 2
        if left is _UNKNOWN or right is _UNKNOWN:
            return self.annotate(expr, result)
        if not ok:
            self.error(
                SemanticErrorKind.INVALID_BINARY_OPERANDS,
                expr,
                f"operador '{op.value}' não aceita {left.value} e {right.value}",
            )
            return _UNKNOWN
        return self.annotate(expr, result)

    def call(self, expr: CallExpr):
        found = [self.value(argument) for argument in expr.arguments]
        symbol = expr.metadata.get("symbol")
        if symbol is None:
            return _UNKNOWN
        expected = symbol.parameter_types
        if len(found) != len(expected):
            self.error(
                SemanticErrorKind.ARITY_MISMATCH,
                expr,
                f"'{symbol.name}' espera {len(expected)} argumento(s) "
                f"e recebeu {len(found)}",
            )
        for argument, got, want in zip(expr.arguments, found, expected):
            if got is not _UNKNOWN and got is not want:
                self.error(
                    SemanticErrorKind.ARGUMENT_TYPE_MISMATCH,
                    argument,
                    f"argumento {got.value}, esperado {want.value}",
                )
        return self.annotate(expr, symbol.type)  # void também é gravado