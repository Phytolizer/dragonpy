from enum import Enum, auto

from pydantic import BaseModel


class SourceLocation(BaseModel):
    filename: str
    line: int
    column: int

    def __str__(self) -> str:
        return f"{self.filename}:{self.line}:{self.column}"


class TokenKind(Enum):
    KW_INT = auto()
    KW_RETURN = auto()

    IDENTIFIER = auto()
    NUMBER = auto()

    OPEN_PARENTHESIS = auto()
    CLOSE_PARENTHESIS = auto()
    OPEN_BRACE = auto()
    CLOSE_BRACE = auto()
    SEMICOLON = auto()


class TokenValue(BaseModel):
    pass


class Identifier(TokenValue):
    value: str


class Number(TokenValue):
    value: int


class Token(BaseModel):
    kind: TokenKind
    location: SourceLocation
    text: str
    value: TokenValue
