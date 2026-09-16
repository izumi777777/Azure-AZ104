from __future__ import annotations

from datetime import date, timedelta

from quiz import DOMAIN_LABELS

DOMAINS = ["identity", "storage", "compute", "network", "monitor"]


def dates_until(exam_day: date, today: date | None = None) -> list[date]:
    today = today or date.today()
    if exam_day < today:
        return []
    days = []
    cur = today
    while cur <= exam_day:
        days.append(cur)
        cur += timedelta(days=1)
    return days


def build_plan(exam_day: date, weak_domain: str | None = None, today: date | None = None) -> list[dict]:
    days = dates_until(exam_day, today)
    n = len(days)
    if n == 0:
        return []
    rows = []
    if n == 1:
        rows.append(_row(days[0], weak_domain or "monitor", "直前復習", 20, "弱点とメモだけ見る"))
        return rows
    if n == 2:
        rows.append(_row(days[0], weak_domain or "identity", "弱点の解き直し", 24, "正誤ログの不正解から"))
        rows.append(_row(days[1], "monitor", "直前復習", 12, "通しは無理せずメモ整理"))
        return rows

    study = days[:-3] if n > 3 else days[:-2]
    tail = days[len(study):]
    for i, day in enumerate(study):
        if weak_domain and i % 6 == 5:
            domain = weak_domain
            title = "弱点の追加日"
            note = f"{DOMAIN_LABELS[domain]}を多めに"
        else:
            domain = DOMAINS[i % 5]
            title = f"{DOMAIN_LABELS[domain]} を回す"
            note = "セット1からその領域を解く"
        rows.append(_row(day, domain, title, 12, note))

    if len(tail) >= 3:
        rows.append(_row(tail[0], weak_domain or "identity", "弱点の解き直し", 24, "正誤ログの不正解だけ"))
        rows.append(_row(tail[1], "compute", "通し試験 60問", 60, "試験モードで時間を測る"))
        rows.append(_row(tail[2], "monitor", "直前・メモ整理", 10, "壁打ちで曖昧な語を潰す"))
    elif len(tail) == 2:
        rows.append(_row(tail[0], weak_domain or "identity", "弱点の解き直し", 24, "正誤ログの不正解から"))
        rows.append(_row(tail[1], "monitor", "直前復習", 12, "メモと壁打ち"))
    return rows


def _row(day: date, domain: str, title: str, target: int, note: str) -> dict:
    return {
        "date": day.isoformat(),
        "domain": domain,
        "title": title,
        "target_questions": target,
        "note": note,
        "done": 0,
    }
