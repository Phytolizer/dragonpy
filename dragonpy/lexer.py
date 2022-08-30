from typing import Iterator, Optional

from dragonpy.token import (
    DecimalConstantToken,
    IdentifierToken,
    SourcePos,
    Token,
    TokenType,
)

_KEYWORDS = {
    "int": TokenType.KwInt,
    "return": TokenType.KwReturn,
    "if": TokenType.KwIf,
    "else": TokenType.KwElse,
    "for": TokenType.KwFor,
    "while": TokenType.KwWhile,
    "do": TokenType.KwDo,
    "break": TokenType.KwBreak,
    "continue": TokenType.KwContinue,
}


class Lexer(Iterator):
    source: str
    token_start: SourcePos
    token_start_ofs: int
    pos: int
    filename: str
    line: int
    col: int

    def __init__(self, source: str, filename: str = "<input>") -> None:
        self.source = source
        self.token_start = SourcePos(filename, 1, 1)
        self.token_start_ofs = 0
        self.pos = 0
        self.filename = filename
        self.line = 1
        self.col = 1

    def __iter__(self):
        return self

    def __next__(self) -> Token:
        return self._lex()

    def _lex(self) -> Token:
        self._skip_whitespace()
        self.token_start = SourcePos(self.filename, self.line, self.col)
        self.token_start_ofs = self.pos
        match self._advance():
            case None:
                raise StopIteration
            case "{":
                return self._add_token(TokenType.OpenBrace)
            case "}":
                return self._add_token(TokenType.CloseBrace)
            case "(":
                return self._add_token(TokenType.OpenParen)
            case ")":
                return self._add_token(TokenType.CloseParen)
            case ";":
                return self._add_token(TokenType.Semicolon)
            case "-":
                if self._peek() == "-":
                    self._advance()
                    return self._add_token(TokenType.MinusMinus)
                else:
                    return self._add_token(TokenType.Minus)
            case "~":
                return self._add_token(TokenType.Tilde)
            case "!":
                if self._peek() == "=":
                    self._advance()
                    return self._add_token(TokenType.BangEqual)
                else:
                    return self._add_token(TokenType.Bang)
            case "+":
                match self._peek():
                    case "=":
                        self._advance()
                        return self._add_token(TokenType.PlusEqual)
                    case "+":
                        self._advance()
                        return self._add_token(TokenType.PlusPlus)
                    case _:
                        return self._add_token(TokenType.Plus)
            case "*":
                if self._peek() == "=":
                    self._advance()
                    return self._add_token(TokenType.StarEqual)
                else:
                    return self._add_token(TokenType.Star)
            case "/":
                if self._peek() == "=":
                    self._advance()
                    return self._add_token(TokenType.SlashEqual)
                else:
                    return self._add_token(TokenType.Slash)
            case "&":
                match self._peek():
                    case "&":
                        self._advance()
                        return self._add_token(TokenType.AmpAmp)
                    case "=":
                        self._advance()
                        return self._add_token(TokenType.AmpEqual)
                    case _:
                        return self._add_token(TokenType.Amp)
            case "|":
                match self._peek():
                    case "|":
                        self._advance()
                        return self._add_token(TokenType.PipePipe)
                    case "=":
                        self._advance()
                        return self._add_token(TokenType.PipeEqual)
                    case _:
                        return self._add_token(TokenType.Pipe)
            case "=":
                if self._peek() == "=":
                    self._advance()
                    return self._add_token(TokenType.EqualEqual)
                else:
                    return self._add_token(TokenType.Equal)
            case "<":
                match self._peek():
                    case "=":
                        self._advance()
                        return self._add_token(TokenType.LessEqual)
                    case "<":
                        self._advance()
                        if self._peek() == "=":
                            self._advance()
                            return self._add_token(TokenType.LessLessEqual)
                        else:
                            return self._add_token(TokenType.LessLess)
                    case _:
                        return self._add_token(TokenType.Less)
            case ">":
                match self._peek():
                    case "=":
                        self._advance()
                        return self._add_token(TokenType.GreaterEqual)
                    case ">":
                        self._advance()
                        if self._peek() == "=":
                            self._advance()
                            return self._add_token(TokenType.GreaterGreaterEqual)
                        else:
                            return self._add_token(TokenType.GreaterGreater)
                    case _:
                        return self._add_token(TokenType.Greater)
            case "%":
                if self._peek() == "=":
                    self._advance()
                    return self._add_token(TokenType.PercentEqual)
                else:
                    return self._add_token(TokenType.Percent)
            case "^":
                if self._peek() == "=":
                    self._advance()
                    return self._add_token(TokenType.CaretEqual)
                else:
                    return self._add_token(TokenType.Caret)
            case ",":
                return self._add_token(TokenType.Comma)
            case "?":
                return self._add_token(TokenType.Question)
            case ":":
                return self._add_token(TokenType.Colon)
            case c if c.isalpha():
                return self._lex_identifier_or_keyword()
            case c if c.isdigit():
                return self._lex_decimal_constant()
            case c:
                raise ValueError(f"Unexpected character: {c}")

    def _skip_whitespace(self) -> None:
        while True:
            c = self._peek()
            if c is None or not c.isspace():
                return

            self._advance()

    def _lex_identifier_or_keyword(self) -> Token:
        while True:
            c = self._peek()
            if c is None or not c.isalnum():
                break
            self._advance()
        try:
            return self._add_token(_KEYWORDS[self._text()])
        except KeyError:
            return IdentifierToken(
                *self._token_args(TokenType.Identifier), value=self._text()
            )

    def _lex_decimal_constant(self) -> Token:
        while True:
            c = self._peek()
            if c is None or not c.isdigit():
                break
            self._advance()
        return DecimalConstantToken(
            *self._token_args(TokenType.DecimalConstant), value=int(self._text())
        )

    def _add_token(self, type: TokenType) -> Token:
        return Token(*self._token_args(type))

    def _token_args(self, type: TokenType) -> tuple[TokenType, str, SourcePos]:
        return (type, self._text(), self.token_start)

    def _text(self) -> str:
        return self.source[self.token_start_ofs : self.pos]

    def _advance(self) -> Optional[str]:
        c = self._peek()
        if c is not None:
            self.pos += 1
            self.col += 1
            if c == "\n":
                self.line += 1
                self.col = 1
        return c

    def _peek(self) -> Optional[str]:
        if self.pos == len(self.source):
            return None
        return self.source[self.pos]
