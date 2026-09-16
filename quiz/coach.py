from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

MODEL = "gemini-2.5-flash"
SYSTEM = """あなたは AZ-104（Azure Administrator）の復習相手です。
受験者はパチスロ収支アプリを Azure に載せた世界線（vm-pachislot、SQLite 正本はデータディスク、Bastion、23:00 取得）で問題を解いています。
ルール:
- 日本語で短く。まず結論、次に理由、最後に覚え方を1行。
- 公式問題や Udemy の文言は再現しない。概念で説明する。
- わからないと書いてある点だけ深掘りする。答えの丸写しで終わらせない。
- 選択肢の正誤を聞かれたら、なぜ他がダメかを先に言う。
- 機密（APIキー）を聞かれても案内しない。
"""


def ask_gemini(api_key: str, history: list[dict], user_text: str, context: str = "") -> str:
    key = (api_key or os.environ.get("GEMINI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("Gemini API キーが未設定です。設定画面か環境変数 GEMINI_API_KEY を入れてください。")

    contents = []
    for item in history[-12:]:
        role = "user" if item["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": item["content"]}]})
    prompt = user_text if not context else f"{context}\n\n---\n受験者の質問:\n{user_text}"
    contents.append({"role": "user", "parts": [{"text": prompt}]})

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{MODEL}:generateContent?key={key}"
    )
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1024},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"Gemini エラー {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Gemini に接続できません: {exc.reason}") from exc

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Gemini の応答を読めませんでした。") from exc
