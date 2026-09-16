# set01.json の約束

1 ファイル = 1 セット。アプリは `questions/*.json` を読む。

| フィールド | 内容 |
|------------|------|
| `id` | セット ID（`set01`） |
| `title` | 画面表示名 |
| `exam` | `AZ-104` |
| `status` | `partial`（36/60）または `complete` |
| `planned_count` | 完成時の問数（60） |
| `time_limit_min` | 試験モードの制限（分） |
| `pass_percent` | 合格目安（70） |
| `case_study` | ホームに出す世界線 |
| `questions[]` | 出題順どおり |

各問:

| フィールド | 内容 |
|------------|------|
| `id` | `A01` など一意 |
| `no` | セット内の通し番号（1 始まり） |
| `domain` | `identity` / `storage` / `compute` / `network` / `monitor` |
| `select_count` | 1〜3。`answer` の個数と一致 |
| `stem` | 本文。正解記号を書かない |
| `code` | Bicep 等。無ければ `null` |
| `preamble` | ケース導入。任意 |
| `choices` | 4 または 5。`key` は A–E |
| `answer` | 正解キーの配列 |
| `explanation` | 提出後・練習の答え合わせで出す |
| `refs` | AZ-104 スキル名 |

採点は集合の一致。部分点なし。
