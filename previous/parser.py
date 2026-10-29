from __future__ import annotations

from collections.abc import Sequence

from Lexer import Token, TokenKind
from ast_nodes import (
    Assignment,
    BinaryExpr,
    BinaryOperator,
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
    Parameter,
    PrintItem,
    PrintStmt,
    Program,
    ReturnStmt,
    SourceSpan,
    Stmt,
    StringLiteral,
    TypeName,
    UnaryExpr,
    UnaryOperator,
    VarDecl,
    WhileStmt,
)


TYPE_START = {TokenKind.KW_INT, TokenKind.KW_BOOL, TokenKind.KW_VOID}
EXPRESSION_START = {
    TokenKind.IDENTIFIER,
    TokenKind.INT_LITERAL,
    TokenKind.KW_FALSE,
    TokenKind.KW_TRUE,
    TokenKind.LEFT_PAREN,
    TokenKind.LOGICAL_NOT,
    TokenKind.MINUS,
}
STATEMENT_START = TYPE_START | {
    TokenKind.IDENTIFIER,
    TokenKind.KW_IF,
    TokenKind.KW_WHILE,
    TokenKind.KW_RETURN,
    TokenKind.KW_PRINT,
    TokenKind.LEFT_BRACE,
}


TYPE_BY_TOKEN = {
    TokenKind.KW_INT: TypeName.INT,
    TokenKind.KW_BOOL: TypeName.BOOL,
    TokenKind.KW_VOID: TypeName.VOID,
}


class ParserError(Exception):
    def __init__(self, token: Token, expected: set[TokenKind]):
        self.token = token
        self.expected = frozenset(expected)
        super().__init__()

    @property
    def line(self) -> int:
        return self.token.line

    @property
    def column(self) -> int:
        return self.token.column

    def __str__(self) -> str:
        names = ", ".join(kind.name for kind in sorted(
            self.expected,
            key=lambda kind: kind.value,
        ))
        return (
            f"erro sintático em {self.line}:{self.column}: esperado {{{names}}}, "
            f"encontrado {self.token.kind.name} ({self.token.lexeme!r})"
        )


class Parser:
    def __init__(self, tokens: Sequence[Token]):
        self.tokens = list(tokens)
        if not self.tokens:
            raise ValueError("a sequência de tokens deve terminar em EOF")
        if self.tokens[-1].kind is not TokenKind.EOF:
            raise ValueError("o último token deve ser EOF")
        if any(token.kind is TokenKind.EOF for token in self.tokens[:-1]):
            raise ValueError("EOF deve aparecer uma única vez, no final")
        self.current = 0

    def peek(self, offset: int = 0) -> Token:
        index = min(self.current + offset, len(self.tokens) - 1)
        return self.tokens[index]

    def check(self, kind: TokenKind) -> bool:
        return self.peek().kind is kind

    def advance(self) -> Token:
        token = self.peek()
        if self.current < len(self.tokens) - 1:
            self.current += 1
        return token

    def match(self, *kinds: TokenKind) -> Token | None:
        if self.peek().kind in kinds:
            return self.advance()
        return None

    def expect(self, kinds: TokenKind | set[TokenKind]) -> Token:
        expected = kinds if isinstance(kinds, set) else {kinds}
        token = self.peek()
        if token.kind not in expected:
            raise ParserError(token, set(expected))
        return self.advance()

    @staticmethod
    def _token_span(token: Token) -> SourceSpan:
        return SourceSpan(
            token.line,
            token.column,
            token.line,
            token.column + len(token.lexeme),
        )

    @staticmethod
    def _start(value: Token | Node) -> tuple[int, int]:
        if isinstance(value, Node):
            return value.span.start_line, value.span.start_column
        return value.line, value.column

    @staticmethod
    def _end(value: Token | Node) -> tuple[int, int]:
        if isinstance(value, Node):
            return value.span.end_line, value.span.end_column
        return value.line, value.column + len(value.lexeme)

    @classmethod
    def _span(cls, first: Token | Node, last: Token | Node) -> SourceSpan:
        start_line, start_column = cls._start(first)
        end_line, end_column = cls._end(last)
        return SourceSpan(start_line, start_column, end_line, end_column)

    def parse(self) -> Program:
        return self.parse_program()

    # program ::= function* EOF
    def parse_program(self) -> Program:
        start = self.peek()
        functions: list[FunctionDecl] = []
        while self.peek().kind in TYPE_START:
            functions.append(self.parse_function())
        eof = self.expect(TokenKind.EOF)
        return Program(functions, span=self._span(start, eof))

    # function ::= type IDENTIFIER ... block
    def parse_function(self) -> FunctionDecl:
        start = self.peek()
        return_type = self.parse_type()
        name = self.expect(TokenKind.IDENTIFIER)
        self.expect(TokenKind.LEFT_PAREN)
        parameters = (
            self.parse_parameter_list()
            if self.peek().kind in TYPE_START
            else []
        )
        self.expect(TokenKind.RIGHT_PAREN)
        body = self.parse_block()
        return FunctionDecl(
            return_type,
            name.lexeme,
            parameters,
            body,
            span=self._span(start, body),
        )

    # type ::= KW_INT | KW_BOOL | KW_VOID
    def parse_type(self) -> TypeName:
        token = self.expect(TYPE_START)
        return TYPE_BY_TOKEN[token.kind]

    def parse_parameter_list(self) -> list[Parameter]:
        parameters = [self.parse_parameter()]
        while self.peek().kind == TokenKind.COMMA:
            self.expect(TokenKind.COMMA)
            parameters.append(self.parse_parameter())
        return parameters

    def parse_parameter(self) -> Parameter:
        start = self.peek()
        parameter_type = self.parse_type()
        name = self.expect(TokenKind.IDENTIFIER)
        return Parameter(
            parameter_type,
            name.lexeme,
            span=self._span(start, name),
        )

    def parse_block(self) -> Block:
        start = self.expect(TokenKind.LEFT_BRACE)
        statements: list[Stmt] = []
        while self.peek().kind in STATEMENT_START:
            statements.append(self.parse_statement())
        end = self.expect(TokenKind.RIGHT_BRACE)
        return Block(statements, span=self._span(start, end))

    def parse_statement(self) -> Stmt:
        kind = self.peek().kind
        if kind in TYPE_START:
            return self.parse_declaration()
        if kind is TokenKind.IDENTIFIER:
            return self.parse_id_or_call_statement()
        if kind is TokenKind.KW_IF:
            return self.parse_if_statement()
        if kind is TokenKind.KW_WHILE:
            return self.parse_while_statement()
        if kind is TokenKind.KW_RETURN:
            return self.parse_return_statement()
        if kind is TokenKind.KW_PRINT:
            return self.parse_print_statement()
        if kind is TokenKind.LEFT_BRACE:
            return self.parse_block()
        raise ParserError(self.peek(), STATEMENT_START)

    def parse_id_or_call_statement(self) -> Stmt:
        # id_or_call_statement ::= IDENTIFIER (ASSIGN expression | LEFT_PAREN arguments RIGHT_PAREN) SEMICOLON
        # Consome o token, ele entra aqui só se for já o identifier,
        start = self.expect(TokenKind.IDENTIFIER)

        # se for o '='
        if self.match(TokenKind.ASSIGN):
            target = IdentifierExpr(start.lexeme, span=self._token_span(start))
            # le as expressões dentro
            value = self.parse_expression()
            # end normalmente sempre vai ser o ';'.
            end = self.expect(TokenKind.SEMICOLON)
            return Assignment(target, value, span=self._span(start, end))

        # se for o '('
        if self.match(TokenKind.LEFT_PAREN):
            # le argumentos
            arguments = self.parse_arguments()
            # esperando o ')'
            right_paren = self.expect(TokenKind.RIGHT_PAREN)
            # CallExpr = nome + argumentos. A diferença entre o CallExpr e o CallStmt
            # é que o Stmt envelopa o dado do Expr, permitindo concatenar como statement.
            # o span do CallExpr vai até o ')' — o ';' é do statement, não da chamada em si.
            call = CallExpr(start.lexeme, arguments, span=self._span(start, right_paren))
            end = self.expect(TokenKind.SEMICOLON)
            return CallStmt(call, span=self._span(start, end))

        # se não veio nem '=' nem '(', a gramática não permite mais nada aqui
        raise ParserError(self.peek(), {TokenKind.ASSIGN, TokenKind.LEFT_PAREN})

    def parse_declaration(self) -> Stmt:
        # declaration ::= type IDENTIFIER (ASSIGN expression)? SEMICOLON
        start = self.peek()
        var_type = self.parse_type()
        name = self.expect(TokenKind.IDENTIFIER)

        # inicializador é opcional, por isso começa None
        initializer = None
        if self.match(TokenKind.ASSIGN):
            initializer = self.parse_expression()

        end = self.expect(TokenKind.SEMICOLON)
        return VarDecl(var_type, name.lexeme, initializer, span=self._span(start, end))

    def parse_if_statement(self) -> Stmt:
        # if_statement ::= KW_IF LEFT_PAREN expression RIGHT_PAREN block (KW_ELSE block)?
        start = self.expect(TokenKind.KW_IF)
        self.expect(TokenKind.LEFT_PAREN)
        expression = self.parse_expression()
        self.expect(TokenKind.RIGHT_PAREN)
        # esse seria o "then"
        then_block = self.parse_block()

        # se tiver um else é isso que verifica, mas antes a gente inicia ele "vazio"
        else_block = None
        if self.match(TokenKind.KW_ELSE):
            else_block = self.parse_block()

        # o end do span tem que ser o último bloco usado: o else, se existir, senão o then
        end = else_block if else_block is not None else then_block

        return IfStmt(expression, then_block, else_block, span=self._span(start, end))

    def parse_while_statement(self) -> Stmt:
        # while_statement ::= KW_WHILE LEFT_PAREN expression RIGHT_PAREN block
        start = self.expect(TokenKind.KW_WHILE)
        self.expect(TokenKind.LEFT_PAREN)
        expression = self.parse_expression()
        self.expect(TokenKind.RIGHT_PAREN)
        while_block = self.parse_block()

        return WhileStmt(expression, while_block, span=self._span(start, while_block))

    def parse_return_statement(self) -> Stmt:
        # return_statement ::= KW_RETURN expression? SEMICOLON
        start = self.expect(TokenKind.KW_RETURN)

        # return pode não ter expressão nenhuma
        expression = None
        # se o próximo já for ';', quer dizer que foi só "return;", então expression fica vazia
        if self.peek().kind != TokenKind.SEMICOLON:
            expression = self.parse_expression()

        end = self.expect(TokenKind.SEMICOLON)
        return ReturnStmt(expression, span=self._span(start, end))

    def parse_print_statement(self) -> Stmt:
        # print_statement ::= KW_PRINT LEFT_PAREN print_item (COMMA print_item)* RIGHT_PAREN SEMICOLON
        lista = []
        start = self.expect(TokenKind.KW_PRINT)
        self.expect(TokenKind.LEFT_PAREN)
        lista.append(self.parse_print_item())  # faltava chamar a função (tinha ficado sem os parênteses)

        while self.peek().kind == TokenKind.COMMA:
            self.expect(TokenKind.COMMA)
            lista.append(self.parse_print_item())
        self.expect(TokenKind.RIGHT_PAREN)

        end = self.expect(TokenKind.SEMICOLON)
        return PrintStmt(lista, span=self._span(start, end))

    def parse_print_item(self) -> PrintItem:
        # print_item ::= expression | string_literals
        # só STRING_LITERAL começa uma string_literals; qualquer outra coisa
        # que comece um print_item válido tem que ser expression.
        if self.peek().kind == TokenKind.STRING_LITERAL:
            return self.parse_string_literals()
        return self.parse_expression()

    def parse_string_literals(self) -> StringLiteral:
        # string_literals ::= STRING_LITERAL+
        # o AST só tem um StringLiteral(value), então concatena os literais consecutivos.
        start = self.expect(TokenKind.STRING_LITERAL)
        parts = [start.value]
        last = start
        while self.peek().kind == TokenKind.STRING_LITERAL:
            last = self.expect(TokenKind.STRING_LITERAL)
            parts.append(last.value)
        value = "".join(str(part) for part in parts)
        return StringLiteral(value, span=self._span(start, last))

    def parse_expression(self) -> Expr:
        # expression ::= logical_or
        # é só delegar pro primeiro nível da cadeia de precedência mesmo
        return self.parse_logical_or()

    def parse_logical_or(self) -> Expr:
        # logical_or ::= logical_and (LOGICAL_OR logical_and)*
        left = self.parse_logical_and()
        while self.peek().kind == TokenKind.LOGICAL_OR:
            self.advance()
            right = self.parse_logical_and()
            left = BinaryExpr(BinaryOperator.LOGICAL_OR, left, right, span=self._span(left, right))
        return left

    def parse_logical_and(self) -> Expr:
        # logical_and ::= equality (LOGICAL_AND equality)*
        left = self.parse_equality()
        while self.peek().kind == TokenKind.LOGICAL_AND:
            self.advance()
            right = self.parse_equality()
            left = BinaryExpr(BinaryOperator.LOGICAL_AND, left, right, span=self._span(left, right))
        return left

    def parse_equality(self) -> Expr:
        # equality ::= relational ((EQUAL_EQUAL | NOT_EQUAL) relational)*
        left = self.parse_relational()
        while self.peek().kind in (TokenKind.EQUAL_EQUAL, TokenKind.NOT_EQUAL):
            token = self.advance()
            right = self.parse_relational()
            operator = (
                BinaryOperator.EQUAL
                if token.kind is TokenKind.EQUAL_EQUAL
                else BinaryOperator.NOT_EQUAL
            )
            left = BinaryExpr(operator, left, right, span=self._span(left, right))
        return left

    def parse_relational(self) -> Expr:
        # relational ::= additive ((LESS | LESS_EQUAL | GREATER | GREATER_EQUAL) additive)*
        relational_ops = {
            TokenKind.LESS: BinaryOperator.LESS,
            TokenKind.LESS_EQUAL: BinaryOperator.LESS_EQUAL,
            TokenKind.GREATER: BinaryOperator.GREATER,
            TokenKind.GREATER_EQUAL: BinaryOperator.GREATER_EQUAL,
        }
        left = self.parse_additive()
        while self.peek().kind in relational_ops:
            token = self.advance()
            right = self.parse_additive()
            left = BinaryExpr(relational_ops[token.kind], left, right, span=self._span(left, right))
        return left

    def parse_additive(self) -> Expr:
        # additive ::= multiplicative ((PLUS | MINUS) multiplicative)*
        left = self.parse_multiplicative()
        while self.peek().kind in (TokenKind.PLUS, TokenKind.MINUS):
            token = self.advance()
            right = self.parse_multiplicative()
            operator = BinaryOperator.ADD if token.kind is TokenKind.PLUS else BinaryOperator.SUBTRACT
            left = BinaryExpr(operator, left, right, span=self._span(left, right))
        return left

    def parse_multiplicative(self) -> Expr:
        # multiplicative ::= unary ((STAR | SLASH | PERCENT) unary)*
        multiplicative_ops = {
            TokenKind.STAR: BinaryOperator.MULTIPLY,
            TokenKind.SLASH: BinaryOperator.DIVIDE,
            TokenKind.PERCENT: BinaryOperator.REMAINDER,
        }
        left = self.parse_unary()
        while self.peek().kind in multiplicative_ops:
            token = self.advance()
            right = self.parse_unary()
            left = BinaryExpr(multiplicative_ops[token.kind], left, right, span=self._span(left, right))
        return left

    def parse_unary(self) -> Expr:
        # unary ::= (LOGICAL_NOT | MINUS) unary | primary
        if self.peek().kind in (TokenKind.LOGICAL_NOT, TokenKind.MINUS):
            token = self.advance()
            # recursivo pra permitir "!!x" ou "--x", por exemplo
            operand = self.parse_unary()
            operator = UnaryOperator.NOT if token.kind is TokenKind.LOGICAL_NOT else UnaryOperator.NEGATE
            return UnaryExpr(operator, operand, span=self._span(token, operand))
        return self.parse_primary()

    def parse_primary(self) -> Expr:
        # primary ::= LEFT_PAREN expression RIGHT_PAREN
        #           | IDENTIFIER (LEFT_PAREN arguments RIGHT_PAREN)?
        #           | INT_LITERAL | KW_TRUE | KW_FALSE
        token = self.peek()

        if token.kind == TokenKind.LEFT_PAREN:
            left_paren = self.advance()
            expr = self.parse_expression()
            right_paren = self.expect(TokenKind.RIGHT_PAREN)
            expr.span = self._span(left_paren, right_paren)  # amplia o span, sem criar nó novo
            return expr

        if token.kind == TokenKind.IDENTIFIER:
            self.advance()
            # se vier '(' logo depois, é uma chamada de função dentro da expressão
            if self.peek().kind == TokenKind.LEFT_PAREN:
                self.advance()
                arguments = self.parse_arguments()
                end = self.expect(TokenKind.RIGHT_PAREN)
                return CallExpr(token.lexeme, arguments, span=self._span(token, end))
            return IdentifierExpr(token.lexeme, span=self._token_span(token))

        if token.kind == TokenKind.INT_LITERAL:
            self.advance()
            return IntLiteral(token.value, span=self._token_span(token))

        if token.kind == TokenKind.KW_TRUE:
            self.advance()
            return BoolLiteral(True, span=self._token_span(token))

        if token.kind == TokenKind.KW_FALSE:
            self.advance()
            return BoolLiteral(False, span=self._token_span(token))

        raise ParserError(token, EXPRESSION_START)

    def parse_arguments(self) -> list[Expr]:
        # arguments ::= (expression (COMMA expression)*)?
        arguments = []
        # se ele achar o ) direto, para e devolve vazia pq não tem argumentos
        if self.peek().kind != TokenKind.RIGHT_PAREN:
            arguments.append(self.parse_expression())
            while self.peek().kind == TokenKind.COMMA:
                self.expect(TokenKind.COMMA)
                arguments.append(self.parse_expression())
        return arguments