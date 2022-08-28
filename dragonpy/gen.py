from io import StringIO
from typing import Optional, TextIO

from dragonpy.ast import (
    AssignExp,
    AssignKind,
    BinaryOpExp,
    BinaryOpKind,
    BlockStatement,
    CommaExp,
    ConditionalExp,
    ConstantExp,
    DeclareStatement,
    Exp,
    ExpStatement,
    Function,
    IfStatement,
    PostfixExp,
    PostfixOpKind,
    Program,
    ReturnStatement,
    Statement,
    UnaryOpExp,
    UnaryOpKind,
    VarExp,
)


class CompileError(RuntimeError):
    pass


_SIZEOF_INT = 8


_VarTable = dict[str, int]


class Compiler:
    _label_counter: int
    _scopes: list[_VarTable]
    _scope: int
    _stack_index: int

    def __init__(self) -> None:
        self._label_counter = 0
        self._scopes = [{}]
        self._scope = 0
        self._stack_index = -_SIZEOF_INT

    def _vars(self) -> _VarTable:
        return self._scopes[self._scope]

    def _put_var(self, name: str, offset: int) -> None:
        self._vars()[name] = offset

    def _get_var(self, name: str, scope: Optional[int] = None) -> int:
        if scope is None:
            scope = self._scope
        if name not in self._scopes[scope].keys():
            if scope == 0:
                raise CompileError(f"Variable not declared: {name}")
            return self._get_var(name, scope - 1)
        return self._scopes[scope][name]
    
    def _push_scope(self) -> None:
        self._scopes.append({})
        self._scope += 1
    
    def _pop_scope(self, out: TextIO) -> None:
        bytes_to_dealloc = len(self._vars()) * _SIZEOF_INT
        print(f"    addq ${bytes_to_dealloc}, %rsp", file=out)
        self._stack_index += bytes_to_dealloc
        self._scopes.pop()
        self._scope -= 1

    def _check_lvalue(self, exp: Exp) -> str:
        match exp:
            case VarExp():
                return exp.name.value
            case _:
                raise CompileError(f"Not an lvalue: {exp}")

    def _generate_label(self, template: str) -> str:
        label_name = template.format(self._label_counter)
        self._label_counter += 1
        return label_name

    def _generate_constant_exp(self, out: TextIO, exp: ConstantExp) -> None:
        print(f"    movq ${exp.value.value}, %rax", file=out)

    def _generate_unary_op_exp(self, out: TextIO, exp: UnaryOpExp) -> None:
        self._generate_exp(out, exp.exp)
        match exp.op:
            case UnaryOpKind.Negation:
                print("    neg %rax", file=out)
            case UnaryOpKind.BitwiseComplement:
                print("    not %rax", file=out)
            case UnaryOpKind.LogicalNegation:
                print("    cmpq $0, %rax", file=out)
                print("    sete %al", file=out)
                print("    movzbq %al, %rax", file=out)
            case UnaryOpKind.Increment:
                var = self._check_lvalue(exp.exp)
                print("    addq $1, %rax", file=out)
                print(f"    movq %rax, {self._get_var(var)}(%rbp)", file=out)
            case UnaryOpKind.Decrement:
                var = self._check_lvalue(exp.exp)
                print("    subq $1, %rax", file=out)
                print(f"    movq %rax, {self._get_var(var)}(%rbp)", file=out)

    def _generate_logical_and_exp(self, out: TextIO, exp: BinaryOpExp) -> None:
        self._generate_exp(out, exp.left)
        print("    cmpq $0, %rax", file=out)
        false_label = self._generate_label(".Lfalse{}")
        print(f"    je {false_label}", file=out)
        self._generate_exp(out, exp.right)
        print("    cmpq $0, %rax", file=out)
        print("    setne %al", file=out)
        print("    movzbq %al, %rax", file=out)
        print(f"{false_label}:", file=out)

    def _generate_logical_or_exp(self, out: TextIO, exp: BinaryOpExp) -> None:
        self._generate_exp(out, exp.left)
        print("    cmpq $0, %rax", file=out)
        true_label = self._generate_label(".Ltrue{}")
        print(f"    jne {true_label}", file=out)
        self._generate_exp(out, exp.right)
        print(f"{true_label}:", file=out)
        print("    cmpq $0, %rax", file=out)
        print("    setne %al", file=out)
        print("    movzbq %al, %rax", file=out)

    def _generate_logical_binary_op_exp(self, out: TextIO, exp: BinaryOpExp) -> None:
        match exp.op:
            case BinaryOpKind.LogicalAnd:
                self._generate_logical_and_exp(out, exp)
            case BinaryOpKind.LogicalOr:
                self._generate_logical_or_exp(out, exp)

    def _generate_binary_op_exp(self, out: TextIO, exp: BinaryOpExp) -> None:
        if exp.op in (BinaryOpKind.LogicalAnd, BinaryOpKind.LogicalOr):
            self._generate_logical_binary_op_exp(out, exp)
            return
        self._generate_exp(out, exp.left)
        print("    pushq %rax", file=out)
        self._generate_exp(out, exp.right)
        print("    popq %rdi", file=out)
        match exp.op:
            case BinaryOpKind.Addition:
                print("    addq %rdi, %rax", file=out)
            case BinaryOpKind.Subtraction:
                print("    subq %rax, %rdi", file=out)
                print("    movq %rdi, %rax", file=out)
            case BinaryOpKind.Multiplication:
                print("    imulq %rdi, %rax", file=out)
            case BinaryOpKind.Division:
                print("    xchg %rax, %rdi", file=out)
                print("    cqto", file=out)
                print("    idivq %rdi", file=out)
            case BinaryOpKind.Equal:
                print("    cmpq %rax, %rdi", file=out)
                print("    sete %al", file=out)
                print("    movzbq %al, %rax", file=out)
            case BinaryOpKind.NotEqual:
                print("    cmpq %rax, %rdi", file=out)
                print("    setne %al", file=out)
                print("    movzbq %al, %rax", file=out)
            case BinaryOpKind.LessThan:
                print("    cmpq %rax, %rdi", file=out)
                print("    setl %al", file=out)
                print("    movzbq %al, %rax", file=out)
            case BinaryOpKind.LessThanOrEqual:
                print("    cmpq %rax, %rdi", file=out)
                print("    setle %al", file=out)
                print("    movzbq %al, %rax", file=out)
            case BinaryOpKind.GreaterThan:
                print("    cmpq %rax, %rdi", file=out)
                print("    setg %al", file=out)
                print("    movzbq %al, %rax", file=out)
            case BinaryOpKind.GreaterThanOrEqual:
                print("    cmpq %rax, %rdi", file=out)
                print("    setge %al", file=out)
                print("    movzbq %al, %rax", file=out)
            case BinaryOpKind.Modulo:
                print("    xchg %rax, %rdi", file=out)
                print("    cqto", file=out)
                print("    idivq %rdi", file=out)
                print("    movq %rdx, %rax", file=out)
            case BinaryOpKind.BitwiseAnd:
                print("    andq %rdi, %rax", file=out)
            case BinaryOpKind.BitwiseOr:
                print("    orq %rdi, %rax", file=out)
            case BinaryOpKind.BitwiseXor:
                print("    xorq %rdi, %rax", file=out)
            case BinaryOpKind.BitwiseLeftShift:
                print("    movq %rdi, %rcx", file=out)
                print("    salq %cl, %rax", file=out)
            case BinaryOpKind.BitwiseRightShift:
                print("    movq %rdi, %rcx", file=out)
                print("    sarq %cl, %rax", file=out)

    def _generate_assign_exp(self, out: TextIO, exp: AssignExp) -> None:
        self._generate_exp(out, exp.right)
        var = self._get_var(exp.left.value)
        match exp.kind:
            case AssignKind.Simple:
                print(f"    movq %rax, {var}(%rbp)", file=out)
            case AssignKind.Add:
                print(f"    movq {var}(%rbp), %rdi", file=out)
                print("    addq %rax, %rdi", file=out)
                print(f"    movq %rdi, {var}(%rbp)", file=out)
            case AssignKind.Subtract:
                print(f"    movq {var}(%rbp), %rdi", file=out)
                print("    subq %rax, %rdi", file=out)
                print(f"    movq %rdi, {var}(%rbp)", file=out)
            case AssignKind.Multiply:
                print(f"    movq {var}(%rbp), %rdi", file=out)
                print("    imulq %rax, %rdi", file=out)
                print(f"    movq %rdi, {var}(%rbp)", file=out)
            case AssignKind.Divide:
                print(f"    movq {var}(%rbp), %rdi", file=out)
                print("    xchg %rax, %rdi", file=out)
                print("    cqto", file=out)
                print("    idivq %rdi", file=out)
                print(f"    movq %rax, {var}(%rbp)", file=out)
            case AssignKind.Modulo:
                print(f"    movq {var}(%rbp), %rdi", file=out)
                print("    xchg %rax, %rdi", file=out)
                print("    cqto", file=out)
                print("    idivq %rdi", file=out)
                print(f"    movq %rdx, {var}(%rbp)", file=out)
            case AssignKind.BitwiseAnd:
                print(f"    movq {var}(%rbp), %rdi", file=out)
                print("    andq %rax, %rdi", file=out)
                print(f"    movq %rdi, {var}(%rbp)", file=out)
            case AssignKind.BitwiseOr:
                print(f"    movq {var}(%rbp), %rdi", file=out)
                print("    orq %rax, %rdi", file=out)
                print(f"    movq %rdi, {var}(%rbp)", file=out)
            case AssignKind.BitwiseXor:
                print(f"    movq {var}(%rbp), %rdi", file=out)
                print("    xorq %rax, %rdi", file=out)
                print(f"    movq %rdi, {var}(%rbp)", file=out)
            case AssignKind.BitwiseLeftShift:
                print(f"    movq {var}(%rbp), %rdi", file=out)
                print("    movq %rax, %rcx", file=out)
                print("    salq %cl, %rdi", file=out)
                print(f"    movq %rdi, {var}(%rbp)", file=out)
            case AssignKind.BitwiseRightShift:
                print(f"    movq {var}(%rbp), %rdi", file=out)
                print("    movq %rax, %rcx", file=out)
                print("    sarq %cl, %rdi", file=out)
                print(f"    movq %rdi, {var}(%rbp)", file=out)

    def _generate_var_exp(self, out: TextIO, exp: VarExp) -> None:
        var = self._get_var(exp.name.value)
        print(f"    movq {var}(%rbp), %rax", file=out)

    def _generate_comma_exp(self, out: TextIO, exp: CommaExp) -> None:
        self._generate_exp(out, exp.left)
        # the result is discarded because it is overwritten
        self._generate_exp(out, exp.right)

    def _generate_postfix_exp(self, out: TextIO, exp: PostfixExp) -> None:
        var = self._check_lvalue(exp.exp)
        self._generate_exp(out, exp.exp)
        match exp.op:
            case PostfixOpKind.Increment:
                print("    addq $1, %rax", file=out)
                print(f"    movq %rax, {self._get_var(var)}(%rbp)", file=out)
            case PostfixOpKind.Decrement:
                print("    subq $1, %rax", file=out)
                print(f"    movq %rax, {self._get_var(var)}(%rbp)", file=out)

    def _generate_conditional_exp(self, out: TextIO, exp: ConditionalExp) -> None:
        self._generate_exp(out, exp.cond)
        print("    cmpq $0, %rax", file=out)
        false_label = self._generate_label(".Lfalse{}")
        print(f"    je {false_label}", file=out)
        self._generate_exp(out, exp.true_exp)
        end_label = self._generate_label(".Lend{}")
        print(f"    jmp {end_label}", file=out)
        print(f"{false_label}:", file=out)
        self._generate_exp(out, exp.false_exp)
        print(f"{end_label}:", file=out)

    def _generate_exp(self, out: TextIO, exp: Exp) -> None:
        match exp:
            case UnaryOpExp():
                self._generate_unary_op_exp(out, exp)
            case BinaryOpExp():
                self._generate_binary_op_exp(out, exp)
            case ConstantExp():
                self._generate_constant_exp(out, exp)
            case AssignExp():
                self._generate_assign_exp(out, exp)
            case VarExp():
                self._generate_var_exp(out, exp)
            case CommaExp():
                self._generate_comma_exp(out, exp)
            case PostfixExp():
                self._generate_postfix_exp(out, exp)
            case ConditionalExp():
                self._generate_conditional_exp(out, exp)
            case _:
                assert False, f"Unknown expression type {type(exp)}"

    def _generate_return_statement(
        self, out: TextIO, statement: ReturnStatement
    ) -> None:
        self._generate_exp(out, statement.exp)
        print("    movq %rbp, %rsp", file=out)
        print("    popq %rbp", file=out)
        print("    ret", file=out)

    def _generate_exp_statement(self, out: TextIO, statement: ExpStatement) -> None:
        self._generate_exp(out, statement.exp)

    def _generate_declare_statement(
        self, out: TextIO, statement: DeclareStatement
    ) -> None:
        if statement.identifier.value in self._vars().keys():
            raise CompileError(
                f"Variable {statement.identifier.value} already declared"
            )
        if statement.initializer:
            self._generate_exp(out, statement.initializer.exp)
        else:
            print("    movq $0, %rax", file=out)
        print("    pushq %rax", file=out)
        self._put_var(statement.identifier.value, self._stack_index)
        self._stack_index -= _SIZEOF_INT

    def _generate_if_statement(self, out: TextIO, statement: IfStatement) -> None:
        self._generate_exp(out, statement.condition)
        print("    cmpq $0, %rax", file=out)
        false_label = self._generate_label(".Lfalse{}")
        print(f"    je {false_label}", file=out)
        self._generate_statement(out, statement.then_statement)
        end_label = self._generate_label(".Lend{}")
        print(f"    jmp {end_label}", file=out)
        print(f"{false_label}:", file=out)
        if statement.else_statement:
            self._generate_statement(out, statement.else_statement)
        print(f"{end_label}:", file=out)
    
    def _generate_block_statement(self, out: TextIO, statement: BlockStatement) -> None:
        self._push_scope()
        for stmt in statement.statements:
            self._generate_statement(out, stmt)
        self._pop_scope(out)

    def _generate_statement(self, out: TextIO, statement: Statement) -> None:
        match statement:
            case ReturnStatement():
                self._generate_return_statement(out, statement)
            case ExpStatement():
                self._generate_exp_statement(out, statement)
            case DeclareStatement():
                self._generate_declare_statement(out, statement)
            case IfStatement():
                self._generate_if_statement(out, statement)
            case BlockStatement():
                self._generate_block_statement(out, statement)
            case _:
                assert False, f"Unknown statement type {type(statement)}"

    def _generate_function(self, out: TextIO, function: Function) -> None:
        print(f"    .globl {function.id.value}", file=out)
        print(f"{function.id.value}:", file=out)
        print("    pushq %rbp", file=out)
        print("    movq %rsp, %rbp", file=out)
        for statement in function.statements:
            self._generate_statement(out, statement)
        print("    movq $0, %rax", file=out)
        print("    movq %rbp, %rsp", file=out)
        print("    popq %rbp", file=out)
        print("    ret", file=out)

    def generate(self, ast: Program) -> str:
        out = StringIO()
        self._generate_function(out, ast.function)
        out.seek(0)
        return out.read()
