import unittest

from app.services.diff_parser import parse_diff


class TestDiffParser(unittest.TestCase):
    def test_simple_unified_diff(self):
        sample = """@@ -1,3 +1,4 @@
 line1
-line2
+line2b
+line3
"""
        result = parse_diff(sample)
        # legacy diff contains joined added lines
        self.assertIn("line2b", result["diff"])
        self.assertIn("line3", result["diff"])

        changed = result["changed_lines"]
        # Expect three entries: removed line2, added line2b, added line3
        self.assertEqual(len(changed), 3)

        self.assertEqual(changed[0]["type"], "removed")
        self.assertEqual(changed[0]["old_line"], 2)

        self.assertEqual(changed[1]["type"], "added")
        self.assertEqual(changed[1]["new_line"], 2)

        self.assertEqual(changed[2]["type"], "added")
        self.assertEqual(changed[2]["new_line"], 3)


if __name__ == "__main__":
    unittest.main()
