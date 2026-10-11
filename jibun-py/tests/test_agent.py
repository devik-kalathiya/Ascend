import json
import os
import shutil
import unittest

from jibun.commands.init import init
from jibun.commands.review import review_day
from jibun.gate import check_day_gate
from jibun.llm import set_llm_override
from jibun.snapshot import diff_since, take_snapshot
from jibun.state import load_state, save_state
from jibun.validator import parse_days
from tests.helpers import CURRICULUM, tmp_project, write

GOOD_REVIEW = json.dumps({
    "summary": "You built the scaffold and the list.",
    "notes": ["Clean file layout"],
    "mistakes": [{"file": "index.html", "severity": "low", "issue": "Missing alt text"}],
    "solutions": [{"mistake": 0, "hint": "Think about screen readers.",
                   "docs": ["https://developer.mozilla.org/en-US/docs/Web/HTML/Element/img"]}],
    "score": 88,
    "next_focus": "Events.",
})


def mock_llm(review=GOOD_REVIEW, fail=False):
    def fake(system, user, json):
        if fail:
            raise RuntimeError("network down")
        return review if "Day-Review Agent" in system else CURRICULUM
    set_llm_override(fake)


def setup_project():
    d = tmp_project()
    write(d, "IDEA.md", "# Todo app\nA simple todo app.")
    mock_llm()
    init(cwd=d)
    return d


def day0_files(d):
    write(d, "index.html", '<html><body><ul id="todos"></ul></body></html>')
    write(d, "src/app.js", "const todos = [];\n")
    write(d, "style.css", "body { margin: 0; }")


class AgentTests(unittest.TestCase):
    def tearDown(self):
        set_llm_override(None)

    def test_init_builds_state_baseline_and_refuses_to_wipe_progress(self):
        d = setup_project()
        state = load_state(d)
        self.assertEqual(state["totalSteps"], 3)
        self.assertEqual(state["currentStep"], 0)
        self.assertTrue(os.path.exists(os.path.join(d, ".jibun", "snapshots", "baseline")))
        self.assertEqual(len(parse_days(os.path.join(d, "INSTRUCTION.md"))), 2)

        save_state(d, {"currentStep": 2})
        mock_llm()
        init(cwd=d)  # no --force: must keep progress
        self.assertEqual(load_state(d)["currentStep"], 2)

    def test_diff_since_reports_added_modified_deleted(self):
        d = tmp_project()
        write(d, "a.js", "one\ntwo\n")
        write(d, "b.js", "gone\n")
        take_snapshot(d, "base")
        write(d, "a.js", "one\nthree\n")
        write(d, "c.js", "new\n")
        os.remove(os.path.join(d, "b.js"))
        diff = diff_since(d, "base")
        self.assertEqual({f["path"]: f["status"] for f in diff["files"]},
                         {"a.js": "modified", "c.js": "added", "b.js": "deleted"})
        self.assertGreaterEqual(diff["totalAdded"], 2)

    def test_review_passes_finished_day_and_unlocks_day1(self):
        d = setup_project()
        day0_files(d)
        save_state(d, {"currentStep": 2})
        days = parse_days(os.path.join(d, "INSTRUCTION.md"))

        self.assertTrue(check_day_gate(d, days, 2)["locked"])  # Day 1 locked before review

        out = review_day(d)
        self.assertEqual(out["day"]["day"], 0)
        self.assertEqual(out["review"]["source"], "ai")
        self.assertTrue(out["review"]["ready"])  # only a "low" mistake
        self.assertTrue(os.path.exists(os.path.join(d, ".jibun", "reviews", "day-0.md")))
        with open(out["file"], encoding="utf-8") as fh:
            self.assertIn("Mistakes", fh.read())
        self.assertTrue(load_state(d)["reviews"]["0"]["passed"])
        self.assertFalse(check_day_gate(d, days, 2)["locked"])  # unlocked

    def test_unfinished_day_does_not_pass_and_ack_overrides(self):
        d = setup_project()
        write(d, "index.html", "<html></html>")  # step 1 incomplete
        days = parse_days(os.path.join(d, "INSTRUCTION.md"))

        out = review_day(d, day_number=0)
        self.assertFalse(out["review"]["ready"])
        self.assertFalse(load_state(d)["reviews"]["0"]["passed"])
        self.assertTrue(check_day_gate(d, days, 2)["locked"])

        review_day(d, day_number=0, ack=True)
        self.assertTrue(load_state(d)["reviews"]["0"]["acknowledged"])
        self.assertFalse(check_day_gate(d, days, 2)["locked"])

    def test_model_claiming_no_mistakes_cannot_pass_failing_day(self):
        d = setup_project()
        mock_llm(review=json.dumps({"summary": "Great!", "notes": [], "mistakes": [],
                                    "solutions": [], "score": 100, "next_focus": ""}))
        out = review_day(d, day_number=0)
        self.assertFalse(out["review"]["ready"])

    def test_offline_fallback_reviews_validation_and_code_smells(self):
        d = setup_project()
        day0_files(d)
        write(d, "src/app.js", "var a = 1;\nconsole.log(1);console.log(2);console.log(3);console.log(4);\n"
                               "try { x(); } catch (e) {}\n// TODO later\n")
        save_state(d, {"currentStep": 2})
        mock_llm(fail=True)

        out = review_day(d, day_number=0)
        self.assertEqual(out["review"]["source"], "offline")
        issues = " | ".join(m["issue"] for m in out["review"]["mistakes"])
        for pat in ("console.log", "var", "catch", "TODO"):
            self.assertIn(pat, issues)
        self.assertGreaterEqual(len(out["review"]["solutions"]), 4)

    def test_malformed_model_json_falls_back_instead_of_crashing(self):
        d = setup_project()
        mock_llm(review="Sorry, here is my review in prose.")
        out = review_day(d, day_number=0)
        self.assertEqual(out["review"]["source"], "offline")

    def test_init_rejects_reply_with_no_steps(self):
        d = tmp_project()
        write(d, "IDEA.md", "idea")
        set_llm_override(lambda system, user, json: "I cannot do that.")
        init(cwd=d)
        self.assertTrue(os.path.exists(os.path.join(d, "INSTRUCTION.raw.md")))
        self.assertIsNone(load_state(d))


if __name__ == "__main__":
    unittest.main()
