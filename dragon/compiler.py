from io import StringIO
from typing import TextIO

from pydantic import BaseModel

from dragon.ast import Expression, Function, Program, Statement

_ASM_HEADER = """
    section .text
    global _start
_start:
    call main
    mov rdi, rax
    mov rax, 60
    syscall
""".strip()


class Compiler(BaseModel):
    def _compile_expression(self, out: TextIO, expression: Expression) -> None:
        print(f"    mov rax, {expression.value}", file=out)
        print("    push rax", file=out)

    def _compile_statement(self, out: TextIO, statement: Statement) -> None:
        self._compile_expression(out, statement.expression)
        print("    pop rax", file=out)
        print("    ret", file=out)

    def _compile_function(self, out: TextIO, function: Function) -> None:
        print(f"    global {function.name}", file=out)
        print(f"{function.name}:", file=out)
        self._compile_statement(out, function.statement)

    def compile(self, program: Program) -> str:
        out = StringIO()
        print(_ASM_HEADER, file=out)
        self._compile_function(out, program.function)
        out.seek(0)
        return out.read()
