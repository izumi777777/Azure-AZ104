# AZ-104 ローカル試験

パチスロ収支基盤を題材にした AZ-104 演習。Udemy 型で 1 問ずつ解く。
収支アプリとは別プロセス。GCP の正本 DB には触れない。

現状はセット1の **60 問**（完成）。

**マニュアル（起動と使い方）:** [docs/manual.md](docs/manual.md)  
**機能設計:** [docs/functional_design.md](docs/functional_design.md) · **内部設計:** [docs/internal_design.md](docs/internal_design.md)

## 起動

```bash
cd Azure-AZ104
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 scripts/build_set01.py   # JSON を作り直すときだけ
python3 app.py
```

ブラウザ: <http://127.0.0.1:5104/>

ホストは `127.0.0.1` のみ。LAN には出さない。

## モード

- **試験**: 提出するまで正解を出さない。制限 100 分（切れても続行可）
- **練習**: 1 問ごとに答え合わせと解説

選択肢は 4〜5。正解は 1〜3 個。指定個数をすべて当てて 1 問正解。

## 学習まわり

ナビから使えます。データは `data/attempts.sqlite`（gitignore）。GCP の正本には触れません。

- **正誤ログ**: 練習の答え合わせと試験提出を問題別に集計
- **予定**: 試験日を入れると、領域ローテ＋直近3日（弱点・通し・直前）
- **メモ**: 自由記述。解説画面からも問題に紐づけられる
- **壁打ち**: Gemini（`gemini-2.5-flash`）。キーは環境変数 `GEMINI_API_KEY` か画面からローカル保存

```bash
python3 -m unittest discover -s tests -v
```

## 問題の正本

- アプリが読む: `questions/set01.json`
- 人間が通読する原案: 収支アプリ側 `docs/az104_pachislot_practice.md`
- 設計: `docs/az104_quiz_app_design.md`
