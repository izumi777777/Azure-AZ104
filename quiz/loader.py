from __future__ import annotations

import json
from pathlib import Path

from quiz import QUESTIONS_DIR

_cache: dict[str, tuple[float, dict]] = {}


def load_set(set_id: str = "set01") -> dict:
    path = QUESTIONS_DIR / f"{set_id}.json"
    mtime = path.stat().st_mtime
    hit = _cache.get(set_id)
    if hit and hit[0] == mtime:
        return hit[1]
    payload = json.loads(path.read_text(encoding="utf-8"))
    questions = payload["questions"]
    payload["_by_id"] = {item["id"]: item for item in questions}
    payload["_by_no"] = {item["no"]: item for item in questions}
    _cache[set_id] = (mtime, payload)
    return payload


def question_by_id(quiz_set: dict, qid: str) -> dict:
    return quiz_set["_by_id"][qid]


def neighbor_ids(quiz_set: dict, qid: str) -> tuple[str | None, str | None]:
    order = [item["id"] for item in quiz_set["questions"]]
    idx = order.index(qid)
    prev_id = order[idx - 1] if idx > 0 else None
    next_id = order[idx + 1] if idx + 1 < len(order) else None
    return prev_id, next_id
