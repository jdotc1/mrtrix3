"""Focused checks for the build-error pager; no project build required."""

import ast
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


class TestBuildErrorPager(unittest.TestCase):
  def setUp(self):
    self.directory = tempfile.TemporaryDirectory(prefix="build logs;literal ")
    self.addCleanup(self.directory.cleanup)
    self.system = Mock()
    self.call = Mock()
    source = Path(__file__).resolve().parents[2] / "build"
    tree = ast.parse(source.read_text())
    handler = next(node for node in tree.body
                   if isinstance(node, ast.FunctionDef)
                   and node.name == "pipe_errors_to_less_handler")
    namespace = {
      "error_stream": "synthetic build error\n",
      "colorize": lambda text: text,
      "os": SimpleNamespace(system=self.system),
      "subprocess": SimpleNamespace(call=self.call),
      "tempfile": SimpleNamespace(NamedTemporaryFile=lambda:
        tempfile.NamedTemporaryFile(dir=self.directory.name)),
    }
    exec(compile(ast.Module(body=[handler], type_ignores=[]),
                 str(source), "exec"), namespace)
    self.handler = namespace["pipe_errors_to_less_handler"]

  def test_pager_receives_one_literal_path(self):
    def inspect_call(arguments):
      self.assertEqual(arguments[:2], ["less", "-RX"])
      self.assertEqual(len(arguments), 3)
      self.assertEqual(Path(arguments[2]).parent, Path(self.directory.name))
      self.assertEqual(Path(arguments[2]).read_bytes(),
                       b"synthetic build error\n")
      return 0
    self.call.side_effect = inspect_call
    self.handler()
    self.call.assert_called_once()
    self.system.assert_not_called()

  def test_missing_pager_is_nonfatal(self):
    self.call.side_effect = OSError("less unavailable")
    self.handler()
    self.call.assert_called_once()
    self.system.assert_not_called()


if __name__ == "__main__":
  unittest.main()
