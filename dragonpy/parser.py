from typing import Optional, cast

from dragonpy.ast import (
    AssignExp,
    AssignKind,
    BinaryOpExp,
    BinaryOpKind,
    ConstantExp,
    DeclareStatement,
    Exp,
    ExpStatement,
    Function,
    Initializer,
    Program,
    ReturnStatement,
    Statement,
    UnaryOpExp,
    UnaryOpKind,
    VarExp,
)
from dragonpy.lexer import Lexer
from dragonpy.token import DecimalConstantToken, IdentifierToken, Token, TokenType


class ParseError(RuntimeError):
    pass


class Parser:
    lexer: Lexer
    buffer: list[Token]

    def __init__(self, source: str, filename: str):
        self.lexer = Lexer(source, filename)
        self.buffer = []

    def _peek(self, n: int) -> Optional[Token]:
        while len(self.buffer) < n:
            try:
                self.buffer.append(next(self.lexer))
            except StopIteration:
                return None
        return self.buffer[n - 1]

    def _advance(self) -> Optional[Token]:
        result: Optional[Token] = None
        if len(self.buffer) > 0:
            result = self.buffer.pop(0)
        else:
            try:
                result = next(self.lexer)
            except StopIteration:
                pass
        return result

    def _advance_nonnull(self, expected: Optional[str] = None) -> Token:
        result = self._advance()
        if result is None:
            if expected is None:
                raise ParseError("Unexpected end of file")
            else:
                raise ParseError(f"Unexpected end of file (expected {expected})")
        return result

    def _expect(self, type: TokenType) -> Token:
        if len(self.buffer) > 0:
            result = self.buffer.pop(0)
        else:
            result = self._advance_nonnull(expected=str(type))
        if result.type != type:
            raise ParseError(
                f"{result.pos}: Unexpected token {result.type} (expected {type})"
            )
        return result

    def _look(self, type: TokenType) -> bool:
        return self._peek(1) is not None and self._peek(1).type == type

    def _match(self, *types: TokenType) -> Optional[Token]:
        tok = self._peek(1)
        if tok is None:
            return None
        if not tok.type in types:
            return None
        self._advance()
        return tok

    def parse(self) -> Program:
        function = self._parse_function()
        end_of_file = self._advance()
        if end_of_file is not None:
            raise ParseError(
                f"{end_of_file.pos}: Unexpected token {end_of_file.type} (expected end of file)"
            )
        return Program(function)

    def _parse_function(self) -> Function:
        int_kw = self._expect(TokenType.KwInt)
        id = cast(IdentifierToken, self._expect(TokenType.Identifier))
        open_paren = self._expect(TokenType.OpenParen)
        close_paren = self._expect(TokenType.CloseParen)
        open_brace = self._expect(TokenType.OpenBrace)
        statements: list[Statement] = []
        while True:
            if self._look(TokenType.CloseBrace):
                break
            statement = self._parse_statement()
            statements.append(statement)
        close_brace = self._expect(TokenType.CloseBrace)
        return Function(
            int_kw, id, open_paren, close_paren, open_brace, statements, close_brace
        )

    def _parse_statement(self) -> Statement:
        if self._look(TokenType.KwReturn):
            return self._parse_return_statement()
        if self._look(TokenType.KwInt):
            return self._parse_declare_statement()
        return self._parse_exp_statement()

    def _parse_return_statement(self) -> Statement:
        return_kw = self._expect(TokenType.KwReturn)
        exp = self._parse_exp()
        semicolon = self._expect(TokenType.Semicolon)
        return ReturnStatement(return_kw, exp, semicolon)

    def _parse_declare_statement(self) -> Statement:
        int_kw = self._expect(TokenType.KwInt)
        id = cast(IdentifierToken, self._expect(TokenType.Identifier))
        initializer: Optional[Initializer] = None
        if tok := self._match(TokenType.Equal):
            exp = self._parse_exp()
            initializer = Initializer(tok, exp)
        semicolon = self._expect(TokenType.Semicolon)
        return DeclareStatement(int_kw, id, initializer, semicolon)

    def _parse_exp_statement(self) -> Statement:
        exp = self._parse_exp()
        semicolon = self._expect(TokenType.Semicolon)
        return ExpStatement(exp, semicolon)

    def _parse_exp(self) -> Exp:
        return self._parse_assign_exp()

    def _parse_assign_exp(self) -> Exp:
        exp = self._parse_logical_or_exp()
        if tok := self._match(
            TokenType.Equal,
            TokenType.PlusEqual,
            TokenType.MinusEqual,
            TokenType.SlashEqual,
            TokenType.StarEqual,
            TokenType.PercentEqual,
            TokenType.LessLessEqual,
            TokenType.GreaterGreaterEqual,
            TokenType.AmpEqual,
            TokenType.PipeEqual,
            TokenType.CaretEqual,
        ):
            if not isinstance(exp, VarExp):
                raise ParseError(
                    f"{exp}: Expected identifier on left-hand side of assignment"
                )
            kind = AssignKind.get(tok)
            exp = AssignExp(exp.name, kind, self._parse_assign_exp())
        return exp

    def _parse_logical_or_exp(self) -> Exp:
        exp = self._parse_logical_and_exp()
        while self._match(TokenType.PipePipe):
            exp = BinaryOpExp(
                BinaryOpKind.LogicalOr, exp, self._parse_logical_and_exp()
            )
        return exp

    def _parse_logical_and_exp(self) -> Exp:
        exp = self._parse_equality_exp()
        while self._match(TokenType.AmpAmp):
            exp = BinaryOpExp(BinaryOpKind.LogicalAnd, exp, self._parse_equality_exp())
        return exp

    def _parse_bitwise_and_exp(self) -> Exp:
        exp = self._parse_bitwise_xor_exp()
        while self._match(TokenType.Amp):
            exp = BinaryOpExp(
                BinaryOpKind.BitwiseAnd, exp, self._parse_bitwise_xor_exp()
            )
        return exp

    def _parse_bitwise_xor_exp(self) -> Exp:
        exp = self._parse_bitwise_or_exp()
        while self._match(TokenType.Caret):
            exp = BinaryOpExp(
                BinaryOpKind.BitwiseXor, exp, self._parse_bitwise_or_exp()
            )
        return exp

    def _parse_bitwise_or_exp(self) -> Exp:
        exp = self._parse_equality_exp()
        while self._match(TokenType.Pipe):
            exp = BinaryOpExp(BinaryOpKind.BitwiseOr, exp, self._parse_equality_exp())
        return exp

    def _parse_equality_exp(self) -> Exp:
        exp = self._parse_relational_exp()
        while tok := self._match(TokenType.EqualEqual, TokenType.BangEqual):
            op = BinaryOpKind.get(tok)
            assert op is not None
            exp = BinaryOpExp(op, exp, self._parse_relational_exp())
        return exp

    def _parse_relational_exp(self) -> Exp:
        exp = self._parse_shift_exp()
        while tok := self._match(
            TokenType.Less,
            TokenType.LessEqual,
            TokenType.Greater,
            TokenType.GreaterEqual,
        ):
            op = BinaryOpKind.get(tok)
            assert op is not None
            exp = BinaryOpExp(op, exp, self._parse_shift_exp())
        return exp

    def _parse_shift_exp(self) -> Exp:
        exp = self._parse_additive_exp()
        while tok := self._match(TokenType.LessLess, TokenType.GreaterGreater):
            op = BinaryOpKind.get(tok)
            assert op is not None
            exp = BinaryOpExp(op, exp, self._parse_additive_exp())
        return exp

    def _parse_additive_exp(self) -> Exp:
        exp = self._parse_term()
        while tok := self._match(TokenType.Plus, TokenType.Minus):
            op = BinaryOpKind.get(tok)
            assert op is not None
            exp = BinaryOpExp(op, exp, self._parse_term())
        return exp

    def _parse_term(self) -> Exp:
        exp = self._parse_factor()
        while tok := self._match(TokenType.Star, TokenType.Slash, TokenType.Percent):
            op = BinaryOpKind.get(tok)
            assert op is not None
            exp = BinaryOpExp(op, exp, self._parse_factor())
        return exp

    def _parse_factor(self) -> Exp:
        if self._match(TokenType.OpenParen):
            exp = self._parse_exp()
            self._expect(TokenType.CloseParen)
            return exp
        if tok := self._match(TokenType.Minus, TokenType.Tilde, TokenType.Bang):
            op = UnaryOpKind.get(tok)
            assert op is not None
            return UnaryOpExp(op, self._parse_factor())
        if tok := self._match(TokenType.DecimalConstant):
            return ConstantExp(cast(DecimalConstantToken, tok))
        if tok := self._match(TokenType.Identifier):
            return VarExp(cast(IdentifierToken, tok))
        tok = self._peek(1)
        raise ParseError(
            f"{tok.pos}: Unexpected token {tok.type} (expected expression)"
        )
