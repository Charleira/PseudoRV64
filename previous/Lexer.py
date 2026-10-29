from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Iterator


class TokenKind(enum.Enum):
    """Classe já implementada: nomes e números não devem ser alterados."""

    EOF = -1

    IDENTIFIER = 1
    INT_LITERAL = 2
    STRING_LITERAL = 3

    KW_INT = 10
    KW_BOOL = 11
    KW_VOID = 12
    KW_TRUE = 13
    KW_FALSE = 14
    KW_IF = 15
    KW_ELSE = 16
    KW_WHILE = 17
    KW_RETURN = 18
    KW_PRINT = 19

    PLUS = 20
    MINUS = 21
    STAR = 22
    SLASH = 23
    PERCENT = 24
    LESS = 25
    LESS_EQUAL = 26
    GREATER = 27
    GREATER_EQUAL = 28
    EQUAL_EQUAL = 29
    NOT_EQUAL = 30
    LOGICAL_AND = 31
    LOGICAL_OR = 32
    LOGICAL_NOT = 33
    ASSIGN = 34

    LEFT_PAREN = 40
    RIGHT_PAREN = 41
    LEFT_BRACE = 42
    RIGHT_BRACE = 43
    COMMA = 44
    SEMICOLON = 45


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    lexeme: str
    value: int | str | bool | None
    line: int
    column: int

    def __str__(self) -> str:
        return (
            f"<{self.kind.value}, {self.kind.name}, {self.lexeme!r}, "
            f"{self.value!r}, {self.line}, {self.column}>"
        )


class LexerError(Exception):
    def __init__(self, message: str, line: int, column: int):
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column

    def __str__(self) -> str:
        return f"erro léxico em {self.line}:{self.column}: {self.message}"


# Palavras reservadas: nome literal -> TokenKind correspondente.
_KEYWORDS: dict[str, TokenKind] = {
    "int": TokenKind.KW_INT,
    "bool": TokenKind.KW_BOOL,
    "void": TokenKind.KW_VOID,
    "true": TokenKind.KW_TRUE,
    "false": TokenKind.KW_FALSE,
    "if": TokenKind.KW_IF,
    "else": TokenKind.KW_ELSE,
    "while": TokenKind.KW_WHILE,
    "return": TokenKind.KW_RETURN,
    "print": TokenKind.KW_PRINT,
}

# Operadores/pontuação de dois caracteres (têm prioridade sobre o prefixo de 1 caractere).
_TWO_CHAR_OPS: dict[str, TokenKind] = {
    "<=": TokenKind.LESS_EQUAL,
    ">=": TokenKind.GREATER_EQUAL,
    "==": TokenKind.EQUAL_EQUAL,
    "!=": TokenKind.NOT_EQUAL,
    "&&": TokenKind.LOGICAL_AND,
    "||": TokenKind.LOGICAL_OR,
}

# Operadores/pontuação de um caractere.
_ONE_CHAR_OPS: dict[str, TokenKind] = {
    "+": TokenKind.PLUS,
    "-": TokenKind.MINUS,
    "*": TokenKind.STAR,
    "/": TokenKind.SLASH,
    "%": TokenKind.PERCENT,
    "<": TokenKind.LESS,
    ">": TokenKind.GREATER,
    "!": TokenKind.LOGICAL_NOT,
    "=": TokenKind.ASSIGN,
    "(": TokenKind.LEFT_PAREN,
    ")": TokenKind.RIGHT_PAREN,
    "{": TokenKind.LEFT_BRACE,
    "}": TokenKind.RIGHT_BRACE,
    ",": TokenKind.COMMA,
    ";": TokenKind.SEMICOLON,
}

# Mapeamento de escapes válidos dentro de STRING_LITERAL.
_STRING_ESCAPES: dict[str, str] = {
    "n": "\n",
    "t": "\t",
    '"': '"',
    "\\": "\\",
}


class Lexer:
    """Converte texto-fonte MicroC em uma sequência de tokens."""

    def __init__(self, source: str):
        self.source = source
        self._length = len(source)
        self._pos = 0
        self._line = 1
        self._column = 1

    # ------------------------------------------------------------------
    # Auxiliares de baixo nível: leitura de caracteres e posição.
    # ------------------------------------------------------------------

    def _peek(self, offset: int = 0) -> str | None:
        idx = self._pos + offset
        if idx < self._length:
            return self.source[idx]
        return None

    def _advance(self) -> str:
        ch = self.source[self._pos]
        self._pos += 1
        if ch == "\n":
            self._line += 1
            self._column = 1
        elif ch == "\r":
            #peek pq a gente tem que ver se é \r\n ou só \r 
            if self._peek() == "\n":
                #'\r\n' conta como UMA quebra de linha só, quem muda a linha é o '\n'm por isso ele quebra
                self._column += 1
            else:
                # '\r' sozinho também é uma quebra de linha alem de cfoluna
                self._line += 1
                self._column = 1
        else:
            self._column += 1
        return ch

    def _at_end(self) -> bool:
        return self._pos >= self._length

    # ------------------------------------------------------------------
    # Descarte de espaços e comentários.
    # ------------------------------------------------------------------

    def _skip_trivia(self) -> None:
        while not self._at_end():
            ch = self._peek()

            if ch in (" ", "\t", "\n", "\r"):
                self._advance()
                continue

            if ch == "/" and self._peek(1) == "/":
                # comentário de linha: descarta até (sem incluir) a quebra de linha ou EOF
                #nota: mudado da versão anterior para incluir o \r também
                while not self._at_end() and self._peek() not in ("\n", "\r"):
                    #verifcando se é ascii
                    if not self._peek().isascii():
                        raise LexerError(
                            f"Caractere não é ASCII",
                            self._line,
                            self._column,
                        )
                    self._advance()
                continue

            if ch == "/" and self._peek(1) == "*":
                start_line, start_col = self._line, self._column
                self._advance()  # '/'
                self._advance()  # '*'
                closed = False
                while not self._at_end():
                    if self._peek() == "*" and self._peek(1) == "/":
                        self._advance()
                        self._advance()
                        closed = True
                        break
                    self._advance()
                if not closed:
                    raise LexerError(
                        "comentário de bloco não terminado", start_line, start_col
                    )
                continue

            break

    # ------------------------------------------------------------------
    # Reconhecimento de cada categoria de token.
    # ------------------------------------------------------------------

    def _scan_identifier(self, line: int, column: int) -> Token:
        chars = []
        while not self._at_end():
            ch = self._peek()
            if ch is not None and ch.isascii() and (ch.isalnum() or ch == "_"):
                chars.append(self._advance())
            else:
                break
        lexeme = "".join(chars)

        kind = _KEYWORDS.get(lexeme)
        if kind is TokenKind.KW_TRUE:
            return Token(kind, lexeme, True, line, column)
        if kind is TokenKind.KW_FALSE:
            return Token(kind, lexeme, False, line, column)
        if kind is not None:
            return Token(kind, lexeme, None, line, column)

        return Token(TokenKind.IDENTIFIER, lexeme, lexeme, line, column)

    def _scan_number(self, line: int, column: int) -> Token:
        chars = []
        while not self._at_end():
            ch = self._peek()
            if ch is not None and ch.isascii() and ch.isdigit():
                chars.append(self._advance())
            else:
                break
        lexeme = "".join(chars)
        return Token(TokenKind.INT_LITERAL, lexeme, int(lexeme), line, column)

    def _scan_string(self, line: int, column: int) -> Token:
        start_line, start_col = line, column
        self._advance()  # consome a aspa de abertura
        raw = ['"']
        value: list[str] = []

        while True:
            if self._at_end():
                raise LexerError(
                    "string literal não terminada (EOF)", start_line, start_col
                )

            ch = self._peek()

            if ch in ("\n", "\r"):
                raise LexerError(
                    "quebra de linha não permitida em string literal",
                    self._line,
                    self._column,
                )
            if ch == '"':
                raw.append(self._advance())
                break

            if ch == "\\":
                bs_line, bs_col = self._line, self._column
                raw.append(self._advance())  # consome a barra invertida
 
                if self._at_end():
                    # barra no fim da entrada: a string simplesmente não terminou
                    raise LexerError(
                        "string literal não terminada (EOF)", start_line, start_col
                    )
 
                if self._peek() in ("\n", "\r"):
                    raise LexerError(
                        "sequência de escape inválida", bs_line, bs_col
                    )
 
                esc_ch = self._peek()
                decoded = _STRING_ESCAPES.get(esc_ch)
                if decoded is None:
                    raise LexerError(
                        "sequência de escape inválida", bs_line, bs_col
                    )
 
                raw.append(self._advance())
                value.append(decoded)
                continue
 
            if not ch.isascii():
                raise LexerError(
                    f"caractere não ASCII {ch!r} em string literal",
                    self._line,
                    self._column,
                )
 
            raw.append(ch)
            value.append(ch)
            self._advance()
 
        lexeme = "".join(raw)
        decoded_value = "".join(value)
        return Token(TokenKind.STRING_LITERAL, lexeme, decoded_value, start_line, start_col)

    def _scan_operator(self, line: int, column: int) -> Token:
        ch = self._advance()

        # Tenta o operador de dois caracteres primeiro (maior prefixo).
        nxt = self._peek()
        if nxt is not None:
            two = ch + nxt
            kind = _TWO_CHAR_OPS.get(two)
            if kind is not None:
                self._advance()
                return Token(kind, two, None, line, column)

        kind = _ONE_CHAR_OPS.get(ch)
        if kind is not None:
            return Token(kind, ch, None, line, column)

        if ch in ("&", "|"):
            raise LexerError(
                f"ocorrência isolada de {ch!r} não é um token válido", line, column
            )

        if not ch.isascii():
            raise LexerError(f"caractere não ASCII {ch!r}", line, column)

        raise LexerError(f"caractere inválido {ch!r}", line, column)

    # ------------------------------------------------------------------
    # Laço principal.
    # ------------------------------------------------------------------

    def tokens(self) -> Iterator[Token]:
        """Produza todos os tokens significativos e um único EOF ao final."""
        while True:
            self._skip_trivia()

            if self._at_end():
                yield Token(TokenKind.EOF, "", None, self._line, self._column)
                return

            start_line, start_column = self._line, self._column
            ch = self._peek()

            if ch == '"':
                yield self._scan_string(start_line, start_column)
                continue

            if ch.isascii() and (ch.isalpha() or ch == "_"):
                yield self._scan_identifier(start_line, start_column)
                continue

            if ch.isascii() and ch.isdigit():
                yield self._scan_number(start_line, start_column)
                continue

            yield self._scan_operator(start_line, start_column)

    def scan(self) -> list[Token]:
        return list(self.tokens())