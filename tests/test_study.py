from datetime import date
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from quiz.coach import ask_gemini
from quiz.schedule import build_plan, dates_until
from quiz.scoring import grade
from quiz.store import AttemptStore


class ScheduleTests(unittest.TestCase):
    def test_inclusive_range(self):
        days = dates_until(date(2026, 9, 20), date(2026, 9, 17))
        self.assertEqual([d.isoformat() for d in days], [
            "2026-09-17", "2026-09-18", "2026-09-19", "2026-09-20",
        ])

    def test_past_exam_is_empty(self):
        self.assertEqual(build_plan(date(2026, 9, 1), today=date(2026, 9, 17)), [])

    def test_final_three_days(self):
        plan = build_plan(date(2026, 10, 1), weak_domain="network", today=date(2026, 9, 17))
        self.assertEqual(plan[0]["date"], "2026-09-17")
        self.assertEqual(plan[-1]["date"], "2026-10-01")
        self.assertEqual(len(plan), 15)
        self.assertEqual(plan[-3]["title"], "弱点の解き直し")
        self.assertEqual(plan[-3]["domain"], "network")
        self.assertEqual(plan[-2]["title"], "通し試験 60問")
        self.assertEqual(plan[-1]["title"], "直前・メモ整理")


class StoreStudyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = AttemptStore(Path(self.tmp.name) / "t.sqlite")

    def tearDown(self):
        self.tmp.cleanup()

    def test_practice_and_exam_logs(self):
        aid = self.store.create("set01", "practice", 100, ["a1"])
        self.store.log_practice(aid, "a1", "identity", False, ["B"])
        self.store.log_practice(aid, "a1", "identity", True, ["A"])
        stats = self.store.question_stats()
        self.assertEqual(stats[0]["qid"], "a1")
        self.assertEqual(stats[0]["n"], 2)
        self.assertEqual(stats[0]["correct"], 1)

        exam_id = self.store.create("set01", "exam", 100, ["a1", "a2"])
        result = grade(
            [
                {"id": "a1", "no": 1, "domain": "identity", "answer": ["A"]},
                {"id": "a2", "no": 2, "domain": "storage", "answer": ["B"]},
            ],
            {"a1": ["A"]},
        )
        self.store.finish(exam_id, result)
        self.store.finish(exam_id, result)
        exam_logs = [s for s in self.store.question_stats() if s["qid"] == "a2"]
        self.assertEqual(exam_logs[0]["n"], 1)
        self.assertEqual(exam_logs[0]["correct"], 0)
        self.assertEqual(self.store.weakest_domain(), "storage")

    def test_memo_schedule_settings(self):
        mid = self.store.save_memo("NSG", "サブネット側", "a1")
        self.assertEqual(self.store.get_memo(mid)["body"], "サブネット側")
        self.store.set_setting("exam_date", "2026-10-01")
        self.store.replace_schedule(build_plan(date(2026, 10, 1), today=date(2026, 9, 17)))
        self.store.toggle_schedule_day("2026-09-17")
        days = self.store.list_schedule()
        self.assertEqual(days[0]["done"], 1)
        self.assertEqual(self.store.get_setting("exam_date"), "2026-10-01")
        self.store.add_chat("user", "NSG?", "a1")
        self.store.add_chat("assistant", "結論: ...", "a1")
        self.assertEqual(len(self.store.list_chat("a1")), 2)


class CoachTests(unittest.TestCase):
    def test_missing_key(self):
        with self.assertRaises(RuntimeError):
            ask_gemini("", [], "hello")


if __name__ == "__main__":
    unittest.main()
