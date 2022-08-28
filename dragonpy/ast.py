from dataclasses import dataclass
from enum import Enum, auto
from io import StringIO
from typing import Optional

from dragonpy.token import DecimalConstantToken, IdentifierToken, Token, TokenType


class Exp:
    pass


@dataclass
class ConstantExp(Exp):
    value: DecimalConstantToken

    def __str__(self) -> str:
        return f"Const({self.value.value})"


class UnaryOpKind(Enum):
    Negation = auto()
    BitwiseComplement = auto()
    LogicalNegation = auto()
    Increment = auto()
    Decrement = auto()

    @staticmethod
    def get(tok: Token) -> Optional["UnaryOpKind"]:
        match tok.type:
            case TokenType.Minus:
                return UnaryOpKind.Negation
            case TokenType.Tilde:
                return UnaryOpKind.BitwiseComplement
            case TokenType.Bang:
                return UnaryOpKind.LogicalNegation
            case TokenType.PlusPlus:
                return UnaryOpKind.Increment
            case TokenType.MinusMinus:
                return UnaryOpKind.Decrement
            case _:
                return None


@dataclass
class UnaryOpExp(Exp):
    op: UnaryOpKind
    exp: Exp

    def __str__(self) -> str:
        return f"UnOp({self.op.name}, {self.exp})"


class BinaryOpKind(Enum):
    Addition = auto()
    Subtraction = auto()
    Multiplication = auto()
    Division = auto()
    LessThan = auto()
    LessThanOrEqual = auto()
    GreaterThan = auto()
    GreaterThanOrEqual = auto()
    Equal = auto()
    NotEqual = auto()
    LogicalAnd = auto()
    LogicalOr = auto()
    Modulo = auto()
    BitwiseAnd = auto()
    BitwiseOr = auto()
    BitwiseXor = auto()
    BitwiseLeftShift = auto()
    BitwiseRightShift = auto()

    @staticmethod
    def get(tok: Token) -> Optional["BinaryOpKind"]:
        match tok.type:
            case TokenType.Plus:
                return BinaryOpKind.Addition
            case TokenType.Minus:
                return BinaryOpKind.Subtraction
            case TokenType.Star:
                return BinaryOpKind.Multiplication
            case TokenType.Slash:
                return BinaryOpKind.Division
            case TokenType.Less:
                return BinaryOpKind.LessThan
            case TokenType.LessEqual:
                return BinaryOpKind.LessThanOrEqual
            case TokenType.Greater:
                return BinaryOpKind.GreaterThan
            case TokenType.GreaterEqual:
                return BinaryOpKind.GreaterThanOrEqual
            case TokenType.EqualEqual:
                return BinaryOpKind.Equal
            case TokenType.BangEqual:
                return BinaryOpKind.NotEqual
            case TokenType.AmpAmp:
                return BinaryOpKind.LogicalAnd
            case TokenType.PipePipe:
                return BinaryOpKind.LogicalOr
            case TokenType.Percent:
                return BinaryOpKind.Modulo
            case TokenType.Amp:
                return BinaryOpKind.BitwiseAnd
            case TokenType.Pipe:
                return BinaryOpKind.BitwiseOr
            case TokenType.Caret:
                return BinaryOpKind.BitwiseXor
            case TokenType.LessLess:
                return BinaryOpKind.BitwiseLeftShift
            case TokenType.GreaterGreater:
                return BinaryOpKind.BitwiseRightShift
            case _:
                return None


@dataclass
class BinaryOpExp(Exp):
    op: BinaryOpKind
    left: Exp
    right: Exp

    def __str__(self) -> str:
        return f"BinOp({self.op.name}, {self.left}, {self.right})"


class AssignKind(Enum):
    Simple = auto()
    Add = auto()
    Subtract = auto()
    Multiply = auto()
    Divide = auto()
    Modulo = auto()
    BitwiseLeftShift = auto()
    BitwiseRightShift = auto()
    BitwiseAnd = auto()
    BitwiseOr = auto()
    BitwiseXor = auto()

    @staticmethod
    def get(tok: Token) -> "AssignKind":
        match tok.type:
            case TokenType.Equal:
                return AssignKind.Simple
            case TokenType.PlusEqual:
                return AssignKind.Add
            case TokenType.MinusEqual:
                return AssignKind.Subtract
            case TokenType.StarEqual:
                return AssignKind.Multiply
            case TokenType.SlashEqual:
                return AssignKind.Divide
            case TokenType.PercentEqual:
                return AssignKind.Modulo
            case TokenType.LessLessEqual:
                return AssignKind.BitwiseLeftShift
            case TokenType.GreaterGreaterEqual:
                return AssignKind.BitwiseRightShift
            case TokenType.AmpEqual:
                return AssignKind.BitwiseAnd
            case TokenType.PipeEqual:
                return AssignKind.BitwiseOr
            case TokenType.CaretEqual:
                return AssignKind.BitwiseXor
            case _:
                assert False, "Invalid assign kind"


@dataclass
class AssignExp(Exp):
    left: IdentifierToken
    kind: AssignKind
    right: Exp

    def __str__(self) -> str:
        return f"Assign({self.left.value}, {self.right})"


@dataclass
class CommaExp(Exp):
    left: Exp
    right: Exp

    def __str__(self) -> str:
        return f"Comma({self.left}, {self.right})"


class PostfixOpKind(Enum):
    Increment = auto()
    Decrement = auto()

    @staticmethod
    def get(tok: Token) -> Optional["PostfixOpKind"]:
        match tok.type:
            case TokenType.PlusPlus:
                return PostfixOpKind.Increment
            case TokenType.MinusMinus:
                return PostfixOpKind.Decrement
            case _:
                return None


@dataclass
class PostfixExp(Exp):
    exp: Exp
    op: PostfixOpKind

    def __str__(self) -> str:
        return f"Postfix({self.exp}, {self.op})"


@dataclass
class ConditionalExp(Exp):
    cond: Exp
    true_exp: Exp
    false_exp: Exp

    def __str__(self) -> str:
        return f"Cond({self.cond}, {self.true_exp}, {self.false_exp})"


@dataclass
class VarExp(Exp):
    name: IdentifierToken

    def __str__(self) -> str:
        return f"Var({self.name.value})"


class Statement:
    pass


@dataclass
class ReturnStatement(Statement):
    return_kw: Token
    exp: Exp
    semicolon: Token

    def __str__(self) -> str:
        return f"RETURN {self.exp}"


@dataclass
class Initializer:
    equal_token: Token
    exp: Exp

    def __str__(self) -> str:
        return f"INIT {self.exp}"


@dataclass
class DeclareStatement(Statement):
    type_kw: Token
    identifier: IdentifierToken
    initializer: Optional[Initializer]
    semicolon: Token

    def __str__(self) -> str:
        out = StringIO()
        out.write(f"DECLARE {self.identifier.value}")
        if self.initializer is not None:
            out.write(f" {self.initializer}")
        out.seek(0)
        return out.read()


@dataclass
class ExpStatement(Statement):
    exp: Exp
    semicolon: Token

    def __str__(self) -> str:
        return f"EXP {self.exp}"


@dataclass
class IfStatement(Statement):
    if_kw: Token
    lparen: Token
    condition: Exp
    rparen: Token
    then_statement: Statement
    else_statement: Optional[Statement]

    def __str__(self) -> str:
        out = StringIO()
        print(f"IF {self.condition} THEN", file=out)
        out.write(" " * 12)
        out.write(str(self.then_statement))
        if self.else_statement is not None:
            print("ELSE", file=out)
            out.write(str(self.else_statement))
        out.seek(0)
        return out.read()


@dataclass
class BlockStatement(Statement):
    lbrace: Token
    statements: list[Statement]
    rbrace: Token

    def __str__(self) -> str:
        out = StringIO()
        print("    BEGIN", file=out)
        for stmt in self.statements:
            print(str(stmt), file=out)
        print("    END", file=out)
        out.seek(0)
        return out.read()


@dataclass
class Function:
    int_kw: Token
    id: IdentifierToken
    open_paren: Token
    close_paren: Token
    open_brace: Token
    statements: list[Statement]
    close_brace: Token

    def __str__(self) -> str:
        out = StringIO()
        print(f"FUN INT {self.id.value}:", file=out)
        print("    params: ()", file=out)
        print("    body:", file=out)
        for statement in self.statements:
            print(f"        {statement}", file=out)
        out.seek(0)
        return out.read().rstrip("\n")


@dataclass
class Program:
    function: Function

    def __str__(self) -> str:
        return str(self.function)
