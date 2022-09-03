import itertools
import subprocess
from os import walk
from pathlib import PurePath
from tempfile import TemporaryDirectory
from typing import Callable, Generator

import pytest
from click.testing import CliRunner

import dragon

_TestFunc = Callable[[], None]
_NUM_STAGES = 1
_CURDIR = PurePath(__file__).parent


def _generate_valid_program_test(path: PurePath) -> _TestFunc:
    def test() -> None:
        runner = CliRunner()
        with TemporaryDirectory() as temp_dir:
            temp_dir = PurePath(temp_dir)
            result = runner.invoke(
                dragon.main, [str(path), "--output", str(temp_dir / "dragon.out")]
            )
            assert result.exit_code == 0
            subprocess.run(
                ["gcc", "-o", str(temp_dir / "gcc.out"), str(path)], check=True
            )
            dragonpy_result = subprocess.run(
                "./dragon.out", cwd=temp_dir, capture_output=True
            )
            gcc_result = subprocess.run("./gcc.out", cwd=temp_dir, capture_output=True)
            assert dragonpy_result.stdout == gcc_result.stdout
            assert dragonpy_result.returncode == gcc_result.returncode

    return test


def _generate_invalid_program_test(path: PurePath) -> _TestFunc:
    def test() -> None:
        runner = CliRunner()
        with TemporaryDirectory() as temp_dir:
            temp_dir = PurePath(temp_dir)
            result = runner.invoke(
                dragon.main, [str(path), "--output", str(temp_dir / "dragon.out")]
            )
            assert result.exit_code != 0

    return test


def _generate_valid_program_tests(
    stage: int,
) -> Generator[tuple[str, _TestFunc], None, None]:
    for (dirpath, _, filenames) in walk(_CURDIR / "cases" / f"stage{stage}" / "valid"):
        for filename in filter(lambda f: PurePath(f).suffix == ".c", filenames):
            yield (
                f"stage{stage}_valid_{filename}",
                _generate_valid_program_test(PurePath(dirpath) / filename),
            )


def _generate_invalid_program_tests(
    stage: int,
) -> Generator[tuple[str, _TestFunc], None, None]:
    for (dirpath, _, filenames) in walk(
        _CURDIR / "cases" / f"stage{stage}" / "invalid"
    ):
        for filename in filter(lambda f: PurePath(f).suffix == ".c", filenames):
            yield (
                f"stage{stage}_invalid_{filename}",
                _generate_invalid_program_test(PurePath(dirpath) / filename),
            )


def _generate_test_stage(stage: int) -> Generator[tuple[str, _TestFunc], None, None]:
    yield from _generate_invalid_program_tests(stage)
    yield from _generate_valid_program_tests(stage)


_TEST_FUNCS = map(_generate_test_stage, map(lambda x: x + 1, range(_NUM_STAGES)))


@pytest.mark.parametrize("name,test_func", itertools.chain(*_TEST_FUNCS))
def test_all(name: str, test_func: _TestFunc) -> None:
    test_func()
