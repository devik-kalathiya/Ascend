import os
import re
import unittest

from jibun.validator import (check_file_quality, parse_all_steps, parse_days,
                             parse_requirements, validate_step)
from tests.helpers import CURRICULUM, tmp_project, write


def curriculum_file():
    d = tmp_project()
    write(d, "INSTRUCTION.md", CURRICULUM)
    return os.path.join(d, "INSTRUCTION.md")


class ValidatorTests(unittest.TestCase):
    def test_parses_steps_without_leaking_next_day_heading(self):
        steps = parse_all_steps(curriculum_file())
        self.assertEqual(len(steps), 3)
        self.assertNotIn("## Day 1", steps[1]["content"])
        self.assertNotIn("Next Steps", steps[2]["content"])

    def test_groups_steps_into_days(self):
        days = parse_days(curriculum_file())
        self.assertEqual([[d["day"], d["steps"]] for d in days], [[0, [1, 2]], [1, [3]]])

    def test_groups_3_steps_per_day_when_day_headings_missing(self):
        d = tmp_project()
        write(d, "INSTRUCTION.md", re.sub(r"^## Day .*$", "", CURRICULUM, flags=re.M))
        days = parse_days(os.path.join(d, "INSTRUCTION.md"))
        self.assertEqual(len(days), 1)
        self.assertEqual(days[0]["steps"], [1, 2, 3])

    def test_contains_is_scoped_to_file_named_in_same_line(self):
        reqs = parse_requirements("**Validation:**\n`src/app.js` exists && contains `addEventListener` && `node_modules/ws` folder exists.")
        self.assertEqual(reqs, [
            {"kind": "file", "target": "src/app.js"},
            {"kind": "contains", "target": "addEventListener", "scope": "src/app.js"},
            {"kind": "directory", "target": "node_modules/ws/"},
        ])

    def test_process_env_is_a_search_term_not_a_file(self):
        reqs = parse_requirements("`src/config.js` exists && `process.env` is used")
        self.assertEqual(reqs, [
            {"kind": "file", "target": "src/config.js"},
            {"kind": "contains", "target": "process.env", "scope": "src/config.js"},
        ])

    def test_step1_fails_when_files_missing_and_passes_when_present(self):
        d = tmp_project()
        step = parse_all_steps(curriculum_file())[0]
        self.assertFalse(validate_step(step["content"], d)["passed"])

        write(d, "index.html", "<html><body></body></html>")
        write(d, "src/app.js", "const a = 1;")
        write(d, "style.css", "body { margin: 0; }")
        self.assertTrue(validate_step(step["content"], d)["passed"])

    def test_empty_file_with_right_name_does_not_pass(self):
        d = tmp_project()
        write(d, "index.html", "<html><body></body></html>")
        write(d, "src/app.js", "")
        write(d, "style.css", "body { margin: 0; }")
        r = validate_step(parse_all_steps(curriculum_file())[0]["content"], d)
        self.assertFalse(r["passed"])
        self.assertRegex(r["reason"], "empty")

    def test_same_file_name_in_another_folder_does_not_pass(self):
        d = tmp_project()
        write(d, "index.html", "<html></html>")
        write(d, "style.css", "a{}")
        write(d, "other/app.js", "const a = 1;")
        r = validate_step(parse_all_steps(curriculum_file())[0]["content"], d)
        self.assertFalse(r["passed"])

    def test_contains_only_counts_text_in_the_named_file(self):
        d = tmp_project()
        step = parse_all_steps(curriculum_file())[1]
        write(d, "index.html", "<html><body></body></html>")
        write(d, "notes.txt", '<ul id="todos">')  # right text, wrong file
        self.assertFalse(validate_step(step["content"], d)["passed"])

        write(d, "index.html", '<html><body><ul id="todos"></ul></body></html>')
        self.assertTrue(validate_step(step["content"], d)["passed"])

    def test_syntax_errors_caught_for_js_json_css_html(self):
        d = tmp_project()
        write(d, "bad.js", "function (")
        write(d, "ok.js", "const a = 1;")
        write(d, "esm.js", "import x from './y.js';\nexport const z = x;")
        write(d, "bad.json", "{ nope")
        write(d, "bad.css", "body { color: red;")
        write(d, "bad.html", "<div><div></div>")
        p = lambda n: os.path.join(d, n)
        self.assertTrue(check_file_quality(p("bad.js")))
        self.assertIsNone(check_file_quality(p("ok.js")))
        self.assertIsNone(check_file_quality(p("esm.js")))
        self.assertRegex(check_file_quality(p("bad.json")), "JSON")
        self.assertRegex(check_file_quality(p("bad.css")), "braces")
        self.assertRegex(check_file_quality(p("bad.html")), "div")


class FallbackSyntaxTests(unittest.TestCase):
    """The pure-Python bracket scanner used when Node is not installed."""

    def test_scanner(self):
        from jibun.validator import _scan_brackets
        self.assertTrue(_scan_brackets("function ("))
        self.assertIsNone(_scan_brackets("import x from './y.js';\nexport const z = x;"))
        self.assertIsNone(_scan_brackets('const r = /[(]/; const s = "a)"; // ok ('))
        self.assertIsNone(_scan_brackets("const t = `a ${b} (`;"))


if __name__ == "__main__":
    unittest.main()
