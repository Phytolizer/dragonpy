import pathlib
import subprocess
from argparse import ArgumentParser
from tempfile import TemporaryDirectory

from dragonpy.gen import Compiler
from dragonpy.parser import Parser


def run(args: list[str]) -> None:
    arg_parser = ArgumentParser("dragonpy", add_help=True)
    arg_parser.add_argument("FILE", help="The file to compile")
    arg_parser.add_argument("-o", "--output", help="The output file", default="a.out")
    arg_parser.add_argument("--dump-ast", help="Dump the AST", action="store_true")
    arg_parser.add_argument(
        "-S", "--assembly", help="Output assembly", action="store_true"
    )

    parsed = arg_parser.parse_args(args)

    filename = parsed.FILE
    with open(filename) as f:
        source = f.read()
    program = Parser(source, filename).parse()
    if parsed.dump_ast:
        print(program)
        exit(0)
    asm = Compiler().generate(program)
    if parsed.assembly:
        with open(parsed.output, "w") as f:
            f.write(asm)
    else:
        with TemporaryDirectory() as dir:
            asm_path = pathlib.PurePath(dir) / "output.s"
            with open(asm_path, "w") as f:
                f.write(asm)
            subprocess.run(["gcc", "-o", parsed.output, asm_path])
