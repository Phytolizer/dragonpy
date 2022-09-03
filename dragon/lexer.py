from typing import Iterator, Optional

from pydantic import BaseModel, PrivateAttr

from dragon.token import (
    Identifier,
    Number,
    SourceLocation,
    Token,
    TokenKind,
    TokenValue,
)

_KEYWORDS: dict[str, TokenKind] = {
    "int": TokenKind.KW_INT,
    "return": TokenKind.KW_RETURN,
}


class Lexer(BaseModel, Iterator):
    source: str
    filename: str
    _token_start = PrivateAttr(0)
    _token_start_location: SourceLocation = PrivateAttr()
    _pos = PrivateAttr(0)
    _line = PrivateAttr(1)
    _column = PrivateAttr(1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._token_start_location = SourceLocation(
            filename=self.filename, line=1, column=1
        )

    def __iter__(self) -> "Lexer":
        return self

    def _peek(self) -> Optional[str]:
        if self._pos >= len(self.source):
            return None
        return self.source[self._pos]

    def _advance(self) -> Optional[str]:
        c = self._peek()
        self._pos += 1
        match c:
            case None:
                return c
            case "\n":
                self._line += 1
                self._column = 1
            case c if c.isspace():
                self._column += 1
            case _:
                pass
        return c

    def _text(self) -> str:
        return self.source[self._token_start : self._pos]

    def _token_args(self, kind: TokenKind) -> tuple[TokenKind, str, SourceLocation]:
        return (kind, self._text(), self._token_start_location)

    def _add_token(self, kind: TokenKind) -> Token:
        (kind, text, location) = self._token_args(kind)
        return Token(
            kind=kind,
            location=location,
            text=text,
            value=TokenValue(),
        )

    def _skip_whitespace(self) -> None:
        while True:
            match self._peek():
                case None:
                    return
                case c if c.isspace():
                    self._advance()
                case _:
                    return

    def _lex_identifier_or_keyword(self):
        while True:
            match self._peek():
                case None:
                    break
                case c if c.isalnum() or c == "_":
                    self._advance()
                case _:
                    break

        text = self._text()
        kind = _KEYWORDS.get(text, TokenKind.IDENTIFIER)
        (kind, text, location) = self._token_args(kind)
        return Token(
            kind=kind,
            text=text,
            location=location,
            value=Identifier(value=text),
        )

    def _lex_number(self):
        while True:
            match self._peek():
                case None:
                    break
                case c if c.isdigit():
                    self._advance()
                case _:
                    break

        (kind, text, location) = self._token_args(TokenKind.NUMBER)
        return Token(
            kind=kind,
            text=text,
            location=location,
            value=Number(value=int(text)),
        )

    def __next__(self) -> Token:
        self._skip_whitespace()
        self._token_start = self._pos
        self._token_start_location = SourceLocation(
            filename=self.filename, line=self._line, column=self._column
        )
        match self._advance():
            case None:
                raise StopIteration
            case "(":
                return self._add_token(TokenKind.OPEN_PARENTHESIS)
            case ")":
                return self._add_token(TokenKind.CLOSE_PARENTHESIS)
            case "{":
                return self._add_token(TokenKind.OPEN_BRACE)
            case "}":
                return self._add_token(TokenKind.CLOSE_BRACE)
            case ";":
                return self._add_token(TokenKind.SEMICOLON)
            case c if c.isalpha():
                return self._lex_identifier_or_keyword()
            case c if c.isdigit():
                return self._lex_number()
            case c:
                raise ValueError(f"Unexpected character: '{c}'")
