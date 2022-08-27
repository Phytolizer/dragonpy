from io import StringIO
from typing import TextIO

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


class Compiler:
    _label_counter: int
    _vars: dict[str, int]
    _stack_index: int

    def __init__(self) -> None:
        self._label_counter = 0
        self._vars = {}
        self._stack_index = -_SIZEOF_INT

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
        if exp.left.value not in self._vars.keys():
            raise CompileError(f"Variable not declared: {exp.left.value}")
        match exp.kind:
            case AssignKind.Simple:
                print(f"    movq %rax, {self._vars[exp.left.value]}(%rbp)", file=out)
            case AssignKind.Add:
                print(f"    movq {self._vars[exp.left.value]}(%rbp), %rdi", file=out)
                print("    addq %rax, %rdi", file=out)
                print(f"    movq %rdi, {self._vars[exp.left.value]}(%rbp)", file=out)
            case AssignKind.Subtract:
                print(f"    movq {self._vars[exp.left.value]}(%rbp), %rdi", file=out)
                print("    subq %rax, %rdi", file=out)
                print(f"    movq %rdi, {self._vars[exp.left.value]}(%rbp)", file=out)
            case AssignKind.Multiply:
                print(f"    movq {self._vars[exp.left.value]}(%rbp), %rdi", file=out)
                print("    imulq %rax, %rdi", file=out)
                print(f"    movq %rdi, {self._vars[exp.left.value]}(%rbp)", file=out)
            case AssignKind.Divide:
                print(f"    movq {self._vars[exp.left.value]}(%rbp), %rdi", file=out)
                print("    xchg %rax, %rdi", file=out)
                print("    cqto", file=out)
                print("    idivq %rdi", file=out)
                print(f"    movq %rax, {self._vars[exp.left.value]}(%rbp)", file=out)
            case AssignKind.Modulo:
                print(f"    movq {self._vars[exp.left.value]}(%rbp), %rdi", file=out)
                print("    xchg %rax, %rdi", file=out)
                print("    cqto", file=out)
                print("    idivq %rdi", file=out)
                print(f"    movq %rdx, {self._vars[exp.left.value]}(%rbp)", file=out)
            case AssignKind.BitwiseAnd:
                print(f"    movq {self._vars[exp.left.value]}(%rbp), %rdi", file=out)
                print("    andq %rax, %rdi", file=out)
                print(f"    movq %rdi, {self._vars[exp.left.value]}(%rbp)", file=out)
            case AssignKind.BitwiseOr:
                print(f"    movq {self._vars[exp.left.value]}(%rbp), %rdi", file=out)
                print("    orq %rax, %rdi", file=out)
                print(f"    movq %rdi, {self._vars[exp.left.value]}(%rbp)", file=out)
            case AssignKind.BitwiseXor:
                print(f"    movq {self._vars[exp.left.value]}(%rbp), %rdi", file=out)
                print("    xorq %rax, %rdi", file=out)
                print(f"    movq %rdi, {self._vars[exp.left.value]}(%rbp)", file=out)
            case AssignKind.BitwiseLeftShift:
                print(f"    movq {self._vars[exp.left.value]}(%rbp), %rdi", file=out)
                print("    movq %rax, %rcx", file=out)
                print("    salq %cl, %rdi", file=out)
                print(f"    movq %rdi, {self._vars[exp.left.value]}(%rbp)", file=out)
            case AssignKind.BitwiseRightShift:
                print(f"    movq {self._vars[exp.left.value]}(%rbp), %rdi", file=out)
                print("    movq %rax, %rcx", file=out)
                print("    sarq %cl, %rdi", file=out)
                print(f"    movq %rdi, {self._vars[exp.left.value]}(%rbp)", file=out)

    def _generate_var_exp(self, out: TextIO, exp: VarExp) -> None:
        if exp.name.value not in self._vars.keys():
            raise CompileError(f"Variable not declared: {exp.name.value}")
        print(f"    movq {self._vars[exp.name.value]}(%rbp), %rax", file=out)

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
        if statement.identifier.value in self._vars.keys():
            raise CompileError(
                f"Variable {statement.identifier.value} already declared"
            )
        if statement.initializer:
            self._generate_exp(out, statement.initializer.exp)
        else:
            print("    movq $0, %rax", file=out)
        print("    pushq %rax", file=out)
        self._vars[statement.identifier.value] = self._stack_index
        self._stack_index -= _SIZEOF_INT

    def _generate_statement(self, out: TextIO, statement: Statement) -> None:
        match statement:
            case ReturnStatement():
                self._generate_return_statement(out, statement)
            case ExpStatement():
                self._generate_exp_statement(out, statement)
            case DeclareStatement():
                self._generate_declare_statement(out, statement)
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
