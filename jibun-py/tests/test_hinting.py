import os
import unittest

from jibun.hinting import build_hint_context, get_hint
from jibun.llm import set_llm_override
from jibun.validator import parse_all_steps
from tests.helpers import CURRICULUM, tmp_project, write


def step1():
    d = tmp_project()
    write(d, "INSTRUCTION.md", CURRICULUM)
    return d, parse_all_steps(os.path.join(d, "INSTRUCTION.md"))[0]["content"]


class HintingTests(unittest.TestCase):
    def tearDown(self):
        set_llm_override(None)

    def test_hint_request_includes_learners_code_and_failures(self):
        d, step = step1()
        write(d, "src/app.js", "const secretMarker = 42;")
        sent = {}

        def fake(system, user, json):
            sent["user"] = user
            return '{"hint": "Look at your file.", "docs": [], "question": "Why?"}'

        set_llm_override(fake)
        h = get_hint(step, d, verify=False)
        self.assertEqual(h["source"], "ai")
        self.assertRegex(sent["user"], "secretMarker")
        self.assertRegex(sent["user"], "Validation currently failing")
        self.assertRegex(build_hint_context(step, d), "does not exist yet")  # index.html missing

    def test_falls_back_to_offline_hint_when_api_unreachable(self):
        d, step = step1()

        def boom(system, user, json):
            raise RuntimeError("offline")

        set_llm_override(boom)
        h = get_hint(step, d, verify=False)
        self.assertEqual(h["source"], "offline")
        self.assertRegex(h["hint"], "Missing")


if __name__ == "__main__":
    unittest.main()
