from typing import Optional, cast

from pydantic import BaseModel, PrivateAttr

from dragon import token
from dragon.ast import Expression, Function, Program, Statement
from dragon.lexer import Lexer
from dragon.token import Token, TokenKind


class ParseError(Exception):
    pass


class Parser(BaseModel):
    _lexer: Lexer = PrivateAttr()
    _buffer: list[Token] = PrivateAttr(default=[])

    def __init__(self, *, source: str, filename: str, **kwargs) -> None:
        super().__init__()
        self._lexer = Lexer(source=source, filename=filename)

    def _peek(self, distance: int) -> Optional[Token]:
        while len(self._buffer) <= distance:
            try:
                self._buffer.append(next(self._lexer))
            except StopIteration:
                return None
        return self._buffer[distance]

    def _advance(self) -> Optional[Token]:
        if self._buffer:
            return self._buffer.pop(0)
        try:
            return next(self._lexer)
        except StopIteration:
            return None

    def _advance_nonnull(self, expected: Optional[str] = None) -> Token:
        token = self._advance()
        if token is None:
            msg = "Unexpected end of file"
            if expected is not None:
                msg += f", expected {expected}"
            raise ParseError(msg)
        return token

    def _expect(self, kind: TokenKind) -> Token:
        token = self._advance_nonnull(expected=kind.name)
        if token.kind != kind:
            msg = (
                f"{token.location}: "
                + f"Unexpected token {token.kind.name}, expected {kind.name}"
            )
            raise ParseError(msg)
        return token

    def _look(self, *kinds: TokenKind) -> bool:
        token = self._peek(0)
        if token is None:
            return False
        return token.kind in kinds

    def _match(self, *kinds: TokenKind) -> Optional[Token]:
        if self._look(*kinds):
            return self._advance()
        return None

    def _parse_expression(self) -> Expression:
        tok = self._expect(TokenKind.NUMBER)
        value = cast(token.Number, tok.value).value
        return Expression(value=value)

    def _parse_statement(self) -> Statement:
        self._expect(TokenKind.KW_RETURN)
        expr = self._parse_expression()
        self._expect(TokenKind.SEMICOLON)
        return Statement(expression=expr)

    def _parse_function(self) -> Function:
        self._expect(TokenKind.KW_INT)
        name_tok = self._expect(TokenKind.IDENTIFIER)
        name = cast(token.Identifier, name_tok.value).value
        self._expect(TokenKind.OPEN_PARENTHESIS)
        self._expect(TokenKind.CLOSE_PARENTHESIS)
        self._expect(TokenKind.OPEN_BRACE)
        stmt = self._parse_statement()
        self._expect(TokenKind.CLOSE_BRACE)
        return Function(name=name, statement=stmt)

    def parse(self) -> Program:
        return Program(function=self._parse_function())
