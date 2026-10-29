from __future__ import annotations

from ast_nodes import (
    Assignment,
    BinaryExpr,
    Block,
    CallExpr,
    CallStmt,
    FunctionDecl,
    IdentifierExpr,
    IfStmt,
    Node,
    Parameter,
    PrintStmt,
    Program,
    ReturnStmt,
    StringLiteral,
    TypeName,
    UnaryExpr,
    VarDecl,
    WhileStmt,
)
from semantic_errors import SemanticDiagnostic, SemanticError, SemanticErrorKind
from symbols import FunctionSymbol, Scope, Symbol, SymbolKind


def resolve_names(program: Program) -> None:
    """Construa escopos, símbolos e vínculos entre usos e declarações."""
    resolver = _NameResolver()
    resolver.run(program)
    if resolver.diagnostics:
        raise SemanticError(resolver.diagnostics)


class _NameResolver:
    def __init__(self) -> None:
        self.functions: dict[str, FunctionSymbol] = {}
        self.diagnostics: list[SemanticDiagnostic] = []
        self.scope: Scope | None = None

    def error(self, kind: SemanticErrorKind, node: Node, message: str) -> None:
        self.diagnostics.append(SemanticDiagnostic(kind, message, node.span))

    # ------------------------------------------------------------------
    def run(self, program: Program) -> None:
        # 1. todas as assinaturas antes dos corpos
        for function in program.functions:
            self.collect(function)
        # 2. main
        self.check_main(program)
        # 3. corpos, em ordem de fonte
        for function in program.functions:
            self.visit_function(function)

    def collect(self, function: FunctionDecl) -> None:
        if function.name in self.functions:  # preserva a primeira entrada
            self.error(
                SemanticErrorKind.DUPLICATE_FUNCTION,
                function,
                f"função '{function.name}' já declarada",
            )
            return
        symbol = FunctionSymbol(
            name=function.name,
            kind=SymbolKind.FUNCTION,
            type=function.return_type,
            declaration=function,
            parameter_types=tuple(p.type for p in function.parameters),
        )
        self.functions[function.name] = symbol
        function.metadata["symbol"] = symbol

    def check_main(self, program: Program) -> None:
        main = self.functions.get("main")
        if main is None:
            self.error(
                SemanticErrorKind.INVALID_MAIN, program, "função 'main' ausente"
            )
        elif main.type is not TypeName.INT or main.parameter_types:
            self.error(
                SemanticErrorKind.INVALID_MAIN,
                main.declaration,
                "main deve ter a assinatura 'int main()'",
            )

    # ------------------------------------------------------------------
    def declare(self, node: Parameter | VarDecl, kind: SymbolKind) -> None:
        assert self.scope is not None
        if node.name in self.scope.symbols:
            self.error(
                SemanticErrorKind.DUPLICATE_DECLARATION,
                node,
                f"'{node.name}' já declarado neste escopo",
            )
            return
        symbol = Symbol(node.name, kind, node.type, node)
        self.scope.symbols[node.name] = symbol
        node.metadata["symbol"] = symbol

    def lookup(self, name: str) -> Symbol | None:
        scope = self.scope
        while scope is not None:  # do mais interno para os pais
            if name in scope.symbols:
                return scope.symbols[name]
            scope = scope.parent
        return None

    # ------------------------------------------------------------------
    def visit_function(self, function: FunctionDecl) -> None:
        # o bloco externo é o escopo da função; parâmetros vivem nele
        scope = Scope(parent=None)
        function.body.metadata["scope"] = scope
        self.scope = scope
        for parameter in function.parameters:
            self.declare(parameter, SymbolKind.PARAMETER)
        for statement in function.body.statements:
            self.visit(statement)
        self.scope = None

    def visit(self, node: Node | None) -> None:
        if node is None:
            return
        if isinstance(node, Block):
            outer = self.scope
            self.scope = Scope(parent=outer)
            node.metadata["scope"] = self.scope
            for statement in node.statements:
                self.visit(statement)
            self.scope = outer
        elif isinstance(node, VarDecl):
            self.declare(node, SymbolKind.VARIABLE)  # antes do inicializador
            self.visit(node.initializer)
        elif isinstance(node, Assignment):
            self.visit(node.target)
            self.visit(node.value)
        elif isinstance(node, CallStmt):
            self.visit(node.call)
        elif isinstance(node, IfStmt):
            self.visit(node.condition)
            self.visit(node.then_block)
            self.visit(node.else_block)
        elif isinstance(node, WhileStmt):
            self.visit(node.condition)
            self.visit(node.body)
        elif isinstance(node, ReturnStmt):
            self.visit(node.value)
        elif isinstance(node, PrintStmt):
            for item in node.items:
                self.visit(item)
        elif isinstance(node, BinaryExpr):
            self.visit(node.left)
            self.visit(node.right)
        elif isinstance(node, UnaryExpr):
            self.visit(node.operand)
        elif isinstance(node, IdentifierExpr):
            symbol = self.lookup(node.name)
            if symbol is None:
                self.error(
                    SemanticErrorKind.UNDECLARED_VARIABLE,
                    node,
                    f"variável '{node.name}' não declarada",
                )
            else:
                node.metadata["symbol"] = symbol
        elif isinstance(node, CallExpr):
            symbol = self.functions.get(node.name)  # só a tabela global
            if symbol is None:
                self.error(
                    SemanticErrorKind.UNDECLARED_FUNCTION,
                    node,
                    f"função '{node.name}' não declarada",
                )
            else:
                node.metadata["symbol"] = symbol
            for argument in node.arguments:  # visita todos, mesmo com erro
                self.visit(argument)
        # IntLiteral, BoolLiteral e StringLiteral não têm nomes a resolver