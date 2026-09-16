from __future__ import annotations


def is_correct(answer: list[str], selected: list[str]) -> bool:
    return set(answer) == set(selected)


def grade(questions: list[dict], answers: dict[str, list[str]]) -> dict:
    total = len(questions)
    correct = 0
    by_domain: dict[str, dict[str, int]] = {}
    details = []
    for item in questions:
        qid = item["id"]
        domain = item["domain"]
        selected = answers.get(qid) or []
        ok = is_correct(item["answer"], selected)
        if ok:
            correct += 1
        bucket = by_domain.setdefault(domain, {"correct": 0, "total": 0})
        bucket["total"] += 1
        if ok:
            bucket["correct"] += 1
        details.append(
            {
                "id": qid,
                "no": item["no"],
                "domain": domain,
                "ok": ok,
                "selected": selected,
                "answer": item["answer"],
            }
        )
    percent = round(100 * correct / total) if total else 0
    return {
        "correct": correct,
        "total": total,
        "percent": percent,
        "by_domain": by_domain,
        "details": details,
    }


def incomplete_questions(questions: list[dict], answers: dict[str, list[str]]) -> list[int]:
    missing = []
    for item in questions:
        selected = answers.get(item["id"]) or []
        if len(selected) != item["select_count"]:
            missing.append(item["no"])
    return missing
