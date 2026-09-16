from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

from quiz import DATA_DIR, DOMAIN_LABELS, SELECT_LABELS
from quiz.coach import ask_gemini
from quiz.loader import load_set, neighbor_ids, question_by_id
from quiz.schedule import build_plan
from quiz.scoring import grade, incomplete_questions, is_correct
from quiz.store import AttemptStore

ROOT = Path(__file__).resolve().parent
JST = ZoneInfo("Asia/Tokyo")


def _secret_key() -> str:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / "secret_key"
    if not path.exists():
        path.write_text(os.urandom(24).hex(), encoding="utf-8")
    return path.read_text(encoding="utf-8").strip()


def _today() -> date:
    return datetime.now(JST).date()


def _mask_key(key: str) -> str:
    key = (key or "").strip()
    if not key:
        return ""
    if len(key) < 8:
        return "設定済"
    return f"••••{key[-4:]}"


def create_app(store_path: Path | None = None) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(ROOT / "templates"),
        static_folder=str(ROOT / "static"),
    )
    app.config["SECRET_KEY"] = _secret_key()
    store = AttemptStore(store_path)

    def current_attempt():
        attempt_id = session.get("attempt_id")
        if not attempt_id:
            return None
        return store.get(attempt_id)

    def question_index():
        quiz_set = load_set("set01")
        return {item["id"]: item for item in quiz_set["questions"]}

    def exam_meta():
        raw = store.get_setting("exam_date")
        exam_day = None
        if raw:
            try:
                exam_day = date.fromisoformat(raw)
            except ValueError:
                exam_day = None
        remaining = (exam_day - _today()).days if exam_day else None
        return {"exam_date": raw, "exam_day": exam_day, "remaining": remaining}

    @app.context_processor
    def inject_labels():
        meta = exam_meta()
        return {
            "domain_labels": DOMAIN_LABELS,
            "select_labels": SELECT_LABELS,
            "exam_date": meta["exam_date"],
            "days_to_exam": meta["remaining"],
        }

    @app.get("/")
    def home():
        quiz_set = load_set("set01")
        today = _today().isoformat()
        schedule = store.list_schedule()
        today_plan = next((row for row in schedule if row["date"] == today), None)
        return render_template(
            "home.html",
            quiz_set=quiz_set,
            today_plan=today_plan,
            domain_stats=store.domain_stats(),
            attempts=store.list_attempts()[:5],
            memos=store.list_memos()[:4],
        )

    @app.post("/exam/start")
    def exam_start():
        mode = request.form.get("mode", "exam")
        if mode not in ("exam", "practice"):
            mode = "exam"
        quiz_set = load_set("set01")
        order = [item["id"] for item in quiz_set["questions"]]
        attempt_id = store.create(
            set_id=quiz_set["id"],
            mode=mode,
            time_limit_min=quiz_set["time_limit_min"],
            order=order,
        )
        session["attempt_id"] = attempt_id
        return redirect(url_for("exam_question", qid=order[0]))

    @app.get("/exam/<qid>")
    def exam_question(qid: str):
        attempt = current_attempt()
        if attempt is None:
            return redirect(url_for("home"))
        if attempt["finished_at"]:
            return redirect(url_for("result", attempt_id=attempt["id"]))
        quiz_set = load_set(attempt["set_id"])
        if qid not in quiz_set["_by_id"]:
            abort(404)
        question = question_by_id(quiz_set, qid)
        prev_id, next_id = neighbor_ids(quiz_set, qid)
        selected = attempt["answers"].get(qid, [])
        checked = None
        if attempt["mode"] == "practice" and request.args.get("checked") == "1" and selected:
            checked = {
                "ok": is_correct(question["answer"], selected),
                "answer": question["answer"],
                "explanation": question["explanation"],
            }
        return render_template(
            "exam.html",
            quiz_set=quiz_set,
            attempt=attempt,
            question=question,
            prev_id=prev_id,
            next_id=next_id,
            selected=selected,
            flagged=qid in attempt["flags"],
            checked=checked,
        )

    @app.post("/exam/<qid>")
    def exam_save(qid: str):
        attempt = current_attempt()
        if attempt is None or attempt["finished_at"]:
            return redirect(url_for("home"))
        quiz_set = load_set(attempt["set_id"])
        if qid not in quiz_set["_by_id"]:
            abort(404)
        question = question_by_id(quiz_set, qid)
        raw = request.form.getlist("choice")
        selected = []
        allowed = {c["key"] for c in question["choices"]}
        for key in raw:
            if key in allowed and key not in selected:
                selected.append(key)
        selected = selected[: question["select_count"]]
        answers = dict(attempt["answers"])
        if selected:
            answers[qid] = selected
        elif qid in answers:
            del answers[qid]
        flags = list(attempt["flags"])
        if request.form.get("flag") == "1":
            if qid not in flags:
                flags.append(qid)
        else:
            flags = [item for item in flags if item != qid]
        store.save_answers(attempt["id"], answers, flags)

        action = request.form.get("action", "stay")
        prev_id, next_id = neighbor_ids(quiz_set, qid)
        if action == "next" and next_id:
            return redirect(url_for("exam_question", qid=next_id))
        if action == "prev" and prev_id:
            return redirect(url_for("exam_question", qid=prev_id))
        goto = request.form.get("goto")
        if goto and goto in quiz_set["_by_id"]:
            return redirect(url_for("exam_question", qid=goto))
        if action == "check" and attempt["mode"] == "practice":
            if selected:
                store.log_practice(
                    attempt["id"],
                    qid,
                    question["domain"],
                    is_correct(question["answer"], selected),
                    selected,
                )
            return redirect(url_for("exam_question", qid=qid, checked=1))
        if action == "finish":
            return redirect(url_for("exam_finish_confirm"))
        return redirect(url_for("exam_question", qid=qid))

    @app.get("/finish")
    def exam_finish_confirm():
        attempt = current_attempt()
        if attempt is None:
            return redirect(url_for("home"))
        quiz_set = load_set(attempt["set_id"])
        missing = incomplete_questions(quiz_set["questions"], attempt["answers"])
        return render_template(
            "finish.html",
            quiz_set=quiz_set,
            attempt=attempt,
            missing=missing,
        )

    @app.post("/finish")
    def exam_finish():
        attempt = current_attempt()
        if attempt is None:
            return redirect(url_for("home"))
        if attempt["finished_at"]:
            return redirect(url_for("result", attempt_id=attempt["id"]))
        quiz_set = load_set(attempt["set_id"])
        result = grade(quiz_set["questions"], attempt["answers"])
        store.finish(attempt["id"], result)
        return redirect(url_for("result", attempt_id=attempt["id"]))

    @app.get("/result/<attempt_id>")
    def result(attempt_id: str):
        attempt = store.get(attempt_id)
        if attempt is None or not attempt["result"]:
            abort(404)
        quiz_set = load_set(attempt["set_id"])
        session["attempt_id"] = attempt_id
        return render_template(
            "result.html",
            quiz_set=quiz_set,
            attempt=attempt,
            result=attempt["result"],
            passed=attempt["result"]["percent"] >= quiz_set["pass_percent"],
        )

    @app.get("/review/<attempt_id>/<qid>")
    def review(attempt_id: str, qid: str):
        attempt = store.get(attempt_id)
        if attempt is None or not attempt["result"]:
            abort(404)
        quiz_set = load_set(attempt["set_id"])
        if qid not in quiz_set["_by_id"]:
            abort(404)
        question = question_by_id(quiz_set, qid)
        prev_id, next_id = neighbor_ids(quiz_set, qid)
        selected = attempt["answers"].get(qid, [])
        ok = is_correct(question["answer"], selected)
        detail_by_id = {row["id"]: row for row in attempt["result"]["details"]}
        return render_template(
            "review.html",
            quiz_set=quiz_set,
            attempt=attempt,
            question=question,
            prev_id=prev_id,
            next_id=next_id,
            selected=selected,
            ok=ok,
            detail_by_id=detail_by_id,
            q_memos=store.memos_for_qid(qid),
        )

    @app.get("/logs")
    def logs():
        quiz_set = load_set("set01")
        by_id = {item["id"]: item for item in quiz_set["questions"]}
        stats = store.question_stats()
        for row in stats:
            item = by_id.get(row["qid"])
            row["no"] = item["no"] if item else None
            row["stem"] = item["stem"] if item else row["qid"]
        return render_template(
            "logs.html",
            quiz_set=quiz_set,
            stats=stats,
            domain_stats=store.domain_stats(),
            attempts=store.list_attempts(),
            recent_wrongs=store.recent_wrongs(12),
            questions=by_id,
        )

    @app.route("/schedule", methods=["GET", "POST"])
    def schedule():
        if request.method == "POST":
            action = request.form.get("action", "save_date")
            if action == "toggle":
                day = request.form.get("date", "")
                store.toggle_schedule_day(day)
                return redirect(url_for("schedule"))
            raw = (request.form.get("exam_date") or "").strip()
            try:
                exam_day = date.fromisoformat(raw)
            except ValueError:
                flash("試験日は YYYY-MM-DD で入れてください。", "error")
                return redirect(url_for("schedule"))
            if exam_day < _today():
                flash("試験日が過去です。今日以降を入れてください。", "error")
                return redirect(url_for("schedule"))
            store.set_setting("exam_date", exam_day.isoformat())
            if action == "generate":
                store.replace_schedule(
                    build_plan(exam_day, store.weakest_domain(), _today())
                )
                flash("試験日までの予定を作り直しました。", "ok")
            else:
                flash("試験日を保存しました。", "ok")
            return redirect(url_for("schedule"))
        days = store.list_schedule()
        today = _today().isoformat()
        done = sum(1 for row in days if row["done"])
        return render_template(
            "schedule.html",
            days=days,
            today=today,
            done=done,
            total=len(days),
            weak_domain=store.weakest_domain(),
        )

    @app.get("/memos")
    def memos():
        return render_template(
            "memos.html",
            memos=store.list_memos(),
            questions=question_index(),
            edit=None,
        )

    @app.get("/memos/<int:memo_id>")
    def memo_edit(memo_id: int):
        item = store.get_memo(memo_id)
        if item is None:
            abort(404)
        return render_template(
            "memos.html",
            memos=store.list_memos(),
            questions=question_index(),
            edit=item,
        )

    @app.post("/memos")
    def memo_save():
        memo_id = request.form.get("memo_id")
        title = (request.form.get("title") or "").strip() or "無題"
        body = (request.form.get("body") or "").strip()
        qid = (request.form.get("qid") or "").strip() or None
        if qid and qid not in question_index():
            qid = None
        saved = store.save_memo(
            title=title,
            body=body,
            qid=qid,
            memo_id=int(memo_id) if memo_id else None,
        )
        flash("メモを保存しました。", "ok")
        next_qid = request.form.get("next_qid")
        attempt_id = request.form.get("attempt_id")
        if next_qid and attempt_id:
            return redirect(url_for("review", attempt_id=attempt_id, qid=next_qid))
        return redirect(url_for("memo_edit", memo_id=saved))

    @app.post("/memos/<int:memo_id>/delete")
    def memo_delete(memo_id: int):
        store.delete_memo(memo_id)
        flash("メモを消しました。", "ok")
        return redirect(url_for("memos"))

    @app.route("/coach", methods=["GET", "POST"])
    def coach():
        quiz_set = load_set("set01")
        by_id = {item["id"]: item for item in quiz_set["questions"]}
        qid = (request.values.get("qid") or "").strip() or None
        if qid and qid not in by_id:
            qid = None
        env_key = os.environ.get("GEMINI_API_KEY", "").strip()
        stored_key = store.get_setting("gemini_api_key")
        if request.method == "POST":
            action = request.form.get("action", "ask")
            if action == "save_key":
                key = (request.form.get("api_key") or "").strip()
                store.set_setting("gemini_api_key", key)
                flash("API キーをこのマシンの SQLite に保存しました。git には出ません。", "ok")
                return redirect(url_for("coach", qid=qid or None))
            if action == "clear":
                store.clear_chat(qid)
                return redirect(url_for("coach", qid=qid or None))
            text = (request.form.get("message") or "").strip()
            if not text:
                flash("質問を書いてください。", "error")
                return redirect(url_for("coach", qid=qid or None))
            store.add_chat("user", text, qid)
            history = store.list_chat(qid)
            api_history = [
                {"role": row["role"], "content": row["content"]}
                for row in history[:-1]
            ]
            context = ""
            if qid:
                question = by_id[qid]
                memos = store.memos_for_qid(qid)
                memo_text = "\n".join(f"- {m['title']}: {m['body']}" for m in memos) or "なし"
                context = (
                    f"対象問題: 問{question['no']} ({DOMAIN_LABELS[question['domain']]}) {question['id']}\n"
                    f"本文: {question['stem']}\n"
                    f"選択肢: "
                    + "; ".join(f"{c['key']}. {c['text']}" for c in question["choices"])
                    + f"\n正解キー: {', '.join(question['answer'])}\n"
                    f"解説: {question['explanation']}\n"
                    f"受験者メモ:\n{memo_text}"
                )
            try:
                reply = ask_gemini(
                    stored_key or env_key,
                    api_history,
                    text,
                    context,
                )
            except RuntimeError as exc:
                flash(str(exc), "error")
                return redirect(url_for("coach", qid=qid or None))
            store.add_chat("assistant", reply, qid)
            return redirect(url_for("coach", qid=qid or None))
        return render_template(
            "coach.html",
            messages=store.list_chat(qid),
            qid=qid,
            question=by_id.get(qid),
            questions=quiz_set["questions"],
            recent_wrongs=store.recent_wrongs(8),
            key_mask=_mask_key(stored_key) or ("環境変数" if env_key else ""),
            has_key=bool(stored_key or env_key),
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5104, debug=False)
