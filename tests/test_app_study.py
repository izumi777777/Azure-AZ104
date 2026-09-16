from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import create_app
from quiz.loader import load_set


class AppStudyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app(Path(self.tmp.name) / "t.sqlite")
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_study_pages(self):
        for path in ("/", "/logs", "/schedule", "/memos", "/coach"):
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 200, path)

    def test_schedule_generate_and_memo(self):
        resp = self.client.post(
            "/schedule",
            data={"action": "generate", "exam_date": "2026-10-01"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("弱点の解き直し".encode("utf-8"), resp.data)

        resp = self.client.post(
            "/memos",
            data={"title": "Bastion", "body": "SSH を開けない", "qid": ""},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Bastion", resp.data)

    def test_practice_check_writes_log(self):
        quiz = load_set("set01")
        first = quiz["questions"][0]
        self.client.post("/exam/start", data={"mode": "practice"})
        self.client.post(
            f"/exam/{first['id']}",
            data={"choice": first["choices"][0]["key"], "action": "check"},
            follow_redirects=True,
        )
        resp = self.client.get("/logs")
        self.assertIn(f"問 {first['no']}".encode("utf-8"), resp.data)

    def test_coach_without_key_does_not_call(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False):
            resp = self.client.post(
                "/coach",
                data={"action": "ask", "message": "NSG とは"},
                follow_redirects=True,
            )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("未設定".encode("utf-8"), resp.data)


if __name__ == "__main__":
    unittest.main()
