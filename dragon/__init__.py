import subprocess
from pathlib import PurePath
from tempfile import TemporaryDirectory

import click
from pydantic import BaseModel

from dragon.compiler import Compiler
from dragon.parser import Parser


class Main(BaseModel):
    file: str
    dump_ast: bool
    assembly: bool
    output: str

    def run(self):
        with open(self.file, "r") as f:
            parser = Parser(source=f.read(), filename=self.file)
            program = parser.parse()
            if self.dump_ast:
                print(program.json(indent=2))
                return

            asm = Compiler().compile(program)
            if self.assembly:
                with open(self.output, "w") as o:
                    o.write(asm)
                return

            with TemporaryDirectory() as td:
                with open(PurePath(td) / "a.s", "w") as o:
                    o.write(asm)
                subprocess.run(["nasm", "-f", "elf64", "a.s"], cwd=td, check=True)
                subprocess.run(
                    ["ld", "-o", self.output, PurePath(td) / "a.o"], check=True
                )


@click.command()
@click.help_option("-h", "--help")
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@click.option("--dump-ast", is_flag=True, help="Dump the AST")
@click.option("-S", "--assembly", is_flag=True, help="Output assembly")
@click.option("-o", "--output", type=click.Path(dir_okay=False), help="Output file")
def main(file: str, dump_ast: bool, assembly: bool, output: str) -> None:
    Main(file=file, dump_ast=dump_ast, assembly=assembly, output=output).run()
