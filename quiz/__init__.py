from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_DIR = ROOT / "questions"
DATA_DIR = ROOT / "data"

DOMAIN_LABELS = {
    "identity": "ID・ガバナンス",
    "storage": "ストレージ",
    "compute": "コンピュート",
    "network": "ネットワーク",
    "monitor": "監視・バックアップ",
}

SELECT_LABELS = {
    1: "1つ選べ",
    2: "該当するものを2つ選べ",
    3: "該当するものを3つ選べ",
}
