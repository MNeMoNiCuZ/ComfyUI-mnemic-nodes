# Run with: python -m unittest discover tests
import importlib.util
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "wildcard_variables", Path(__file__).parent.parent / "utils" / "wildcard_variables.py"
)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
split = _module.split_variable_definitions


class SplitVariableDefinitionsTest(unittest.TestCase):
    """Tests for split_variable_definitions."""
    def test_simple(self):
        """Plain definitions are extracted and removed."""
        self.assertEqual(split("${animal=!cat} A ${animal}"), ([("animal", "cat")], " A ${animal}"))

    def test_nested_value(self):
        """Values with nested {...} blocks are kept whole."""
        self.assertEqual(
            split("${c=!{red|{dark|light} blue}} x ${c}"),
            ([("c", "{red|{dark|light} blue}")], " x ${c}"),
        )

    def test_use_before_definition(self):
        """A ${name} use before its definition is left alone."""
        self.assertEqual(split("A ${a} then ${a=!dog} end"), ([("a", "dog")], "A ${a} then  end"))

    def test_unclosed_keeps_old_behaviour(self):
        """Unbalanced definitions end at the first } on the line, like the old regex."""
        self.assertEqual(split("${a=!{red|blue}"), ([("a", "{red|blue")], ""))
        self.assertEqual(split("${a=!{open"), ([], "${a=!{open"))

    def test_no_definitions(self):
        """Text without definitions is returned unchanged."""
        self.assertEqual(split("no vars $5 {a|b}"), ([], "no vars $5 {a|b}"))


if __name__ == "__main__":
    unittest.main()
