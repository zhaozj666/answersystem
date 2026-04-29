from __future__ import annotations

import py_compile
import unittest
from pathlib import Path


class BackendCompileTest(unittest.TestCase):
    def test_backend_python_files_compile(self) -> None:
        backend_dir = Path(__file__).resolve().parent.parent / "backend"
        python_files = sorted(backend_dir.rglob("*.py"))

        self.assertTrue(python_files, "expected backend python files to exist")

        for file_path in python_files:
            with self.subTest(file=str(file_path.relative_to(backend_dir.parent))):
                py_compile.compile(str(file_path), doraise=True)


if __name__ == "__main__":
    unittest.main()
