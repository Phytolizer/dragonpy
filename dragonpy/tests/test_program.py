import itertools
import os
import subprocess
from pathlib import Path, PurePath
from tempfile import TemporaryDirectory
from typing import Callable, Generator

import pytest

import dragonpy

_NUM_STAGES = 7
_CURDIR = PurePath(__file__).parent


TestFunc = Callable[[], None]


def generate_valid_program_test(filepath: PurePath) -> TestFunc:
    def test() -> None:
        skip_on_failure = filepath.name.startswith("skip_on_failure_")
        with TemporaryDirectory() as dir:
            dir = PurePath(dir)
            try:
                dragonpy.run(["--output", str(dir / "dragonpy.out"), str(filepath)])
            except Exception:
                if skip_on_failure:
                    pytest.skip("Test skipped on failure")
                else:
                    raise
            subprocess.run(["gcc", "-o", str(dir / "gcc.out"), str(filepath)])
            dragonpy_out = subprocess.run([str(dir / "dragonpy.out")])
            gcc_out = subprocess.run([str(dir / "gcc.out")])
            assert dragonpy_out.returncode == gcc_out.returncode

    return test


def generate_valid_program_tests(
    stage: int,
) -> Generator[tuple[str, TestFunc], None, None]:
    for (dirpath, _, filenames) in os.walk(
        _CURDIR / "examples" / f"stage_{stage}" / "valid"
    ):
        for filename in filter(lambda fn: PurePath(fn).suffix == ".c", filenames):
            yield (
                f"valid_stage{stage}_{filename}",
                generate_valid_program_test(PurePath(dirpath) / filename),
            )


def generate_invalid_program_test(filepath: PurePath) -> TestFunc:
    def test() -> None:
        with TemporaryDirectory() as dir:
            dir = PurePath(dir)
            try:
                dragonpy.run(["--output", str(dir / "dragonpy.out"), str(filepath)])
            except Exception:
                pass
            assert not Path(dir / "dragonpy.out").exists()

    return test


def generate_invalid_program_tests(
    stage: int,
) -> Generator[tuple[str, TestFunc], None, None]:
    for (dirpath, _, filenames) in os.walk(
        _CURDIR / "examples" / f"stage_{stage}" / "invalid"
    ):
        for filename in filter(lambda fn: PurePath(fn).suffix == ".c", filenames):
            yield (
                f"invalid_stage{stage}_{filename}",
                generate_invalid_program_test(PurePath(dirpath) / filename),
            )


def generate_test_stage(
    stage: int,
) -> Generator[tuple[str, TestFunc], None, None]:
    yield from generate_valid_program_tests(stage)
    yield from generate_invalid_program_tests(stage)


_TEST_FUNCS = map(generate_test_stage, range(1, _NUM_STAGES + 1))


@pytest.mark.parametrize("name,test_func", itertools.chain(*_TEST_FUNCS))
def test_all(name: str, test_func: TestFunc) -> None:
    test_func()
