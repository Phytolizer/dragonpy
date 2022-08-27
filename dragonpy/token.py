from dataclasses import dataclass
from enum import Enum, auto


@dataclass
class SourcePos:
    filename: str
    line: int
    col: int

    def __str__(self) -> str:
        return f"{self.filename}:{self.line}:{self.col}"


class TokenType(Enum):
    KwInt = auto()
    KwReturn = auto()
    Identifier = auto()
    OpenParen = auto()
    CloseParen = auto()
    OpenBrace = auto()
    CloseBrace = auto()
    DecimalConstant = auto()
    Semicolon = auto()
    Minus = auto()
    Tilde = auto()
    Bang = auto()
    Plus = auto()
    Star = auto()
    Slash = auto()
    AmpAmp = auto()
    PipePipe = auto()
    EqualEqual = auto()
    BangEqual = auto()
    Less = auto()
    LessEqual = auto()
    Greater = auto()
    GreaterEqual = auto()
    Percent = auto()
    Amp = auto()
    Pipe = auto()
    Caret = auto()
    LessLess = auto()
    GreaterGreater = auto()
    Equal = auto()
    PlusEqual = auto()
    MinusEqual = auto()
    SlashEqual = auto()
    StarEqual = auto()
    PercentEqual = auto()
    LessLessEqual = auto()
    GreaterGreaterEqual = auto()
    AmpEqual = auto()
    PipeEqual = auto()
    CaretEqual = auto()


@dataclass
class Token:
    type: TokenType
    text: str
    pos: SourcePos


@dataclass
class IdentifierToken(Token):
    value: str


@dataclass
class DecimalConstantToken(Token):
    value: int
