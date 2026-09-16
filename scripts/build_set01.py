#!/usr/bin/env python3
"""セット1（60問）を questions/set01.json に書き出す。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "questions" / "set01.json"

BICEP_C06 = """resource nsg 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: 'nsg-pachislot'
  location: location
  properties: {
    securityRules: [
      {
        name: 'Deny-SSH-Internet'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Deny'
          protocol: 'Tcp'
          sourceAddressPrefix: 'Internet'
          destinationPortRange: '22'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
        }
      }
    ]
  }
}"""

CASE_PREAMBLE = (
    "夜稼働画面が「データなし」。最大回転が当日 1834G で 4000G 未達、という話とは別に、"
    "そもそも 23:00 取得が VM まで届いていない疑いがある。"
)


def q(
    qid: str,
    no: int,
    domain: str,
    stem: str,
    choices: list[tuple[str, str]],
    answer: list[str],
    explanation: str,
    refs: list[str],
    code: str | None = None,
    preamble: str | None = None,
) -> dict:
    item = {
        "id": qid,
        "no": no,
        "domain": domain,
        "select_count": len(answer),
        "stem": stem,
        "code": code,
        "choices": [{"key": k, "text": t} for k, t in choices],
        "answer": answer,
        "explanation": explanation,
        "refs": refs,
    }
    if preamble:
        item["preamble"] = preamble
    return item


QUESTIONS = [
    q(
        "A01", 1, "identity",
        "監査法人の同僚に、ポータルから VM のメトリックとバックアップの成功/失敗だけ見せたい。設定変更、ディスクのデタッチ、ストレージアカウントキーの閲覧はさせたくない。どの組みが適切か。",
        [
            ("A", "サブスクリプションで Owner、リソースグループに削除ロック"),
            ("B", "rg-pachislot-prod で Reader"),
            ("C", "VM だけ Contributor、ストレージは何も付けない"),
            ("D", "サブスクリプションで User Access Administrator"),
        ],
        ["B"],
        "閲覧だけなら Reader。Owner / Contributor はキー閲覧やディスク操作まで通る。User Access Administrator は権限の付与ができて広すぎる。",
        ["Manage access to Azure resources"],
    ),
    q(
        "D01", 2, "network",
        "いまの「22 番を世界に開けず IAP で入る」を Azure で最も近い形にする。",
        [
            ("A", "VM にパブリック IP を付け、NSG で自分の自宅 IP だけ 22 を Allow"),
            ("B", "パブリック IP なし + Azure Bastion + Internet→22 Deny"),
            ("C", "5000 番を 0.0.0.0/0 で Allow し、SSH は閉じる"),
            ("D", "ExpressRoute を個人契約する"),
        ],
        ["B"],
        "IAP SSH の翻訳は Bastion + パブリック IP なし。自宅 IP Allow は IP が変わるし、22 をインターネットに出す。",
        ["Implement Azure Bastion"],
    ),
    q(
        "B01", 3, "storage",
        "Databricks 学習用に hall_daily_data の Parquet を同僚ワークスペースへ渡す。アカウントキーは渡したくない。後から一発で無効化したい。",
        [
            ("A", "コンテナを公開（匿名読み取り）にする"),
            ("B", "アカウントキーを 1 通のメールで送り、終わったらローテーションする"),
            ("C", "格納アクセスポリシー付きの SAS を発行し、終わったらポリシーを消す"),
            ("D", "AzCopy のログインを同僚の個人 Microsoft アカウントに付ける"),
        ],
        ["C"],
        "格納アクセスポリシーを消せば、発行済み SAS をまとめて無効化できる。匿名公開はホール名ダンプには不適。アカウントキーは権限が広すぎる。",
        ["Create and use shared access signature (SAS) tokens"],
    ),
    q(
        "C01", 4, "compute",
        "月曜 03:30 の ML 再学習で B1s がスワップだらけになる。Web の夜稼働画面は止めずに、学習だけ強くしたい。コストも 24 時間 D シリーズにはしたくない。",
        [
            ("A", "VM を常時 D4s にする"),
            ("B", "Virtual Machine Scale Set を min=3 にする"),
            ("C", "学習ジョブだけ Container Apps か ACI で時限起動し、VM は Web + SQLite のまま"),
            ("D", "Availability Set に 2 台目を足して両方で学習する"),
        ],
        ["C"],
        "本 VM に同居させない。Scale Set 3 台は個人アプリではコスト事故。",
        ["Provision a container by using Azure Container Instances"],
    ),
    q(
        "E01", 5, "monitor",
        "23:00 のホール取得で CPU が 10 分だけ 90% になるのは正常。CPU 90% のメトリックアラートを 24 時間有効にすると毎晩通知が来る。ノイズを減らす良い手段はどれか。",
        [
            ("A", "アラートを削除する"),
            ("B", "アラート処理ルールで 22:50–00:10 を抑制し、取得失敗はログアラートで別検知する"),
            ("C", "VM をその時間だけ deallocate する"),
            ("D", "メトリックのサンプリングを 1 日に 1 回にする"),
        ],
        ["B"],
        "予定されたスパイクは処理ルールで抑制。取得の成否は別シグナル。deallocate は本末転倒。",
        ["Set up alert rules, action groups, and alert processing rules"],
    ),
    q(
        "A02", 6, "identity",
        "同僚は自社の Entra テナントを持っている。こちらのテナントに「メンバー」として作るとライセンスと監査上まずい。どう招待するか。",
        [
            ("A", "ローカルアカウントを VM に作り、Bastion で共有する"),
            ("B", "外部ユーザー（ゲスト）として招待し、必要なスコープだけ RBAC を付ける"),
            ("C", "ストレージアカウントキーをメールする"),
            ("D", "所有者アカウントのパスワードを 1 日だけ共有する"),
        ],
        ["B"],
        "他テナントはゲスト招待。VM ローカル帳は監査不能。キーやパスワード共有は試験でも実務でも不可。",
        ["Manage external users"],
    ),
    q(
        "D02", 7, "network",
        "誤って VM にパブリック IP を付け、NSG に Inbound Allow * → 5000 優先度 110 を足した。Deny SSH は優先度 100 のまま。インターネットから Flask に届くか。",
        [
            ("A", "届かない。Deny が常に Allow に勝つ"),
            ("B", "届く。同じ方向では数値が小さい（優先度が高い）ルールが先。100 は 22 だけなので、110 の 5000 Allow が有効"),
            ("C", "届くが Bastion 経由だけ"),
            ("D", "既定の DenyAll が 65500 なので 5000 は常に閉じる"),
        ],
        ["B"],
        "優先度は数値が小さいほど強い。Deny 22 は 5000 に影響しない。既定 DenyAll より明示 Allow が先。",
        ["Evaluate effective security rules in NSGs"],
    ),
    q(
        "B02", 8, "storage",
        "ホール日次ダンプの使い方は次の通り。直近 7 日は夜稼働の検算でよく読む。30 日超はほぼ見ない。90 日超は学習用の凍結コピー。ライフサイクルで適切なのはどれか。",
        [
            ("A", "すべて Archive に即時移行し、読むときだけ再hydrate"),
            ("B", "7 日後 Cool、90 日後 Archive"),
            ("C", "すべて Premium SSD に置く"),
            ("D", "バージョン管理を無効化し、上書きだけにする"),
        ],
        ["B"],
        "夜稼働の 7 日と、学習用の長期凍結はライフサイクルの定番。全部 Archive は hydrate 待ちで夜稼働に間に合わない。",
        ["Configure blob lifecycle management"],
    ),
    q(
        "C02", 9, "compute",
        "「データセンター 1 棟の電源障害でも VM を残したい。更新ドメインの分散は不要。台数は 1 のまま」。どれか。",
        [
            ("A", "Availability Set"),
            ("B", "Availability Zone に 1 台置く"),
            ("C", "Scale Set の手動スケール 1"),
            ("D", "Azure Site Recovery だけ設定し、ゾーンは気にしない"),
        ],
        ["B"],
        "1 台でデータセンター障害に備えるならゾーン。セットは複数 VM の更新／障害ドメイン用。",
        ["Deploy virtual machines to availability zones and availability sets"],
    ),
    q(
        "E02", 10, "monitor",
        "LINE にエラーを飛ばしたい。Azure Monitor の標準チャネルに LINE は無い。AZ-104 の範囲で組める形はどれか。",
        [
            ("A", "メトリックをポータルで見るだけ"),
            ("B", "アクション グループの Webhook（試験ではメール・SMS・Webhook）で外部 API に渡す"),
            ("C", "NSG フローログを LINE が直接購読する"),
            ("D", "Bastion のセッション記録を LINE に転送する"),
        ],
        ["B"],
        "アクション グループが試験の答え。LINE 固有は出ないが Webhook が対応づけ。",
        ["Set up alert rules, action groups, and alert processing rules"],
    ),
    q(
        "A03", 11, "identity",
        "ポータル掃除中に rg-pachislot-prod を消しかけた。正本 SQLite がディスクごと消える。再発防止で最初にやることはどれか。",
        [
            ("A", "VM を Availability Set に入れ直す"),
            ("B", "リソースグループに CanNotDelete ロックを掛ける"),
            ("C", "ストレージを Archive 層にする"),
            ("D", "NSG で 22 番を Deny する"),
        ],
        ["B"],
        "正本消滅は削除ロックの典型。可用性セットも NSG も消しミスは止めない。",
        ["Configure resource locks"],
    ),
    q(
        "D03", 12, "network",
        "ストレージをインターネットに出さず、VM からだけバックアップしたい。より厳格なのはどれか。",
        [
            ("A", "ストレージファイアウォールで「すべてのネットワーク」"),
            ("B", "サービスエンドポイントだけ"),
            ("C", "Private Endpoint を snet-pe に置き、パブリックアクセスを無効化"),
            ("D", "SAS の HTTPS 指定だけ"),
        ],
        ["C"],
        "PE + パブリック無効が一番きつい。サービスエンドポイントは Microsoft のバックボーン経由だがパブリック エンドポイントは残る。",
        ["Configure private endpoints for Azure PaaS"],
    ),
    q(
        "B03", 13, "storage",
        "2026-09-01 に SQLite が malformed になり、復旧コピーを残した。Blob 上のバックアップを「消したつもりが消えていた」を防ぎたい。",
        [
            ("A", "LRS を GRS にするだけで十分"),
            ("B", "Blob のソフトデリートとバージョン管理を有効化する"),
            ("C", "コンテナのアクセスレベルを Blob にする"),
            ("D", "ライフサイクルで 1 日後に削除する"),
        ],
        ["B"],
        "malformed 復旧の再発防止は、消した・上書きしたを戻せるソフトデリートとバージョン。GRS はリージョン障害用。",
        ["Configure soft delete for blobs and containers"],
    ),
    q(
        "C03", 14, "compute",
        "SQLite 正本がある VM を App Service（Linux、コードデプロイ）に移す提案。いちばんの問題はどれか。",
        [
            ("A", "App Service は Python を実行できない"),
            ("B", "ローカルディスクが揮発的で、正本 SQLite がデプロイやスケールで消える／共有できない"),
            ("C", "App Service は NSG を付けられないので必ず全世界公開になる"),
            ("D", "TLS 証明書が使えない"),
        ],
        ["B"],
        "App Service はアプリ公開には強いが、この正本の置き方と対立する。TLS や Python は問題ではない。",
        ["Create and configure Azure App Service"],
    ),
    q(
        "E03", 15, "monitor",
        "malformed の翌日、「昨日 23:00 時点のディスク」に戻したい。リージョン横断のアプリフェールオーバーは不要。",
        [
            ("A", "Azure Site Recovery で西日本にフェールオーバー"),
            ("B", "Azure Backup の復旧ポイントからデータディスクを復元する"),
            ("C", "Blob の Archive を再hydrate するだけ（ディスクは触らない）"),
            ("D", "VM サイズを変えると自動でスナップショットに戻る"),
        ],
        ["B"],
        "昨日のディスクは Backup。ASR は別リージョンへのフェールオーバー。",
        ["Perform backup and restore operations by using Azure Backup"],
    ),
    q(
        "A04", 16, "identity",
        "いま B1s 相当で月額がほぼゼロに近い。サイズを D2s に上げると課金が乗る。コスト超過を「起きたあと」ではなく「近づいたとき」に知りたい。",
        [
            ("A", "Azure Advisor のセキュリティ推奨だけ有効化"),
            ("B", "予算（Budget）とコストアラートをサブスクリプションに設定する"),
            ("C", "VM の自動シャットダウンを 23:00 にする"),
            ("D", "リソースグループを別サブスクリプションに移す"),
        ],
        ["B"],
        "Advisor は推奨。超過の閾値通知は Budget。23:00 停止は取得ジョブを殺す。",
        ["Manage costs by using alerts, budgets, and Azure Advisor"],
    ),
    q(
        "D04", 17, "network",
        "夜稼働が「データなし」。VM から取得元サイトへ出られない疑い。まず使うものはどれか。",
        [
            ("A", "Azure Advisor のコスト推奨"),
            ("B", "Network Watcher の接続モニター／IP フロー検証で、送信 NSG と実経路を見る"),
            ("C", "Site Recovery のフェールオーバー"),
            ("D", "Availability Set の障害ドメイン"),
        ],
        ["B"],
        "データなしのインフラ側は送信経路。試験の Network Watcher シナリオそのもの。",
        ["Use Azure Network Watcher and Connection monitor"],
    ),
    q(
        "B04", 18, "storage",
        "Flask が毎分 SQLite に書く。バックアップ先とは別に、アプリの正本を Azure Files の SMB 共有に移す提案が出た。AZ-104 的に正しい判断はどれか。",
        [
            ("A", "Azure Files は WAL と同時書き込み向きなので移すべき"),
            ("B", "正本はデータディスクのまま。Files は設定ファイルや静的共有向き。SQLite のロックと遅延に向かない"),
            ("C", "Blob のホット層に pachislot.db を直接マウントする"),
            ("D", "ページ Blob に SQLite を置き、複数 VM から同時マウントする"),
        ],
        ["B"],
        "WAL の SQLite を Files に置くとロックと遅延で壊れる。正本はデータディスク。Blob はバックアップと Parquet 用。",
        ["Create and configure a file share in Azure Files"],
    ),
    q(
        "C04", 19, "compute",
        "Playwright による取得を本 VM で常駐させるとメモリが足りない。ポータルだけで「コンテナを短時間上げる」ならどれか。",
        [
            ("A", "Azure Kubernetes Service を本番必須にする"),
            ("B", "Azure Container Instances または Container Apps"),
            ("C", "Cloud Shell を開きっぱなしにする"),
            ("D", "Bastion 上で Docker を動かす"),
        ],
        ["B"],
        "ポータル範囲のコンテナは ACI / Container Apps。AKS は運用過大。Bastion は踏み台。",
        ["Provision and manage containers in the Azure portal"],
    ),
    q(
        "E04", 20, "monitor",
        "「東日本が 1 時間以上死んだら、西日本で VM ごと起したい。RPO は約 1 時間」。Backup の日次復元では足りない。",
        [
            ("A", "予算アラート"),
            ("B", "Azure Site Recovery で Azure to Azure レプリケーション"),
            ("C", "Availability Set"),
            ("D", "Blob ソフトデリート"),
        ],
        ["B"],
        "RPO 1 時間のリージョン障害は ASR。日次 Backup では 1 時間に届かない。",
        ["Configure Azure Site Recovery for Azure resources"],
    ),
    q(
        "A05", 21, "identity",
        "「VM にパブリック IP を付けるデプロイを禁止したい」。最も直接的な手段はどれか。",
        [
            ("A", "NSG の既定ルールに頼る"),
            ("B", "Azure Policy でパブリック IP の作成を Deny"),
            ("C", "Bastion を 2 台にする"),
            ("D", "タグ PublicIP=false を付ける"),
        ],
        ["B"],
        "タグは強制力がない。Policy の Deny が作成そのものを止める。",
        ["Implement and manage Azure Policy"],
    ),
    q(
        "D05", 22, "network",
        "Databricks 学習用ワークスペースが別 VNet vnet-dbx にある。vnet-pachislot の Private Endpoint 付き Blob を、ピアリング経由で読ませたい。最初に必要なのはどれか。",
        [
            ("A", "パブリック IP を VM に付ける"),
            ("B", "VNet ピアリング（必要なら Private Endpoint の DNS を両 VNet で解決できるようにする）"),
            ("C", "両方の VNet を削除して 1 つに作り直す"),
            ("D", "ロードバランサーをインターネット向きにする"),
        ],
        ["B"],
        "ピアリングと Private DNS ゾーンのリンク。LB やパブリック IP は不要。",
        ["Create and configure virtual network peering"],
    ),
    q(
        "B05", 23, "storage",
        "ストレージファイアウォールで「選択した仮想ネットワークからだけ」にした。VM から AzCopy でバックアップが失敗する。最初に疑うのはどれか。",
        [
            ("A", "NSG の受信 443 が Deny だから"),
            ("B", "サービスエンドポイントまたは Private Endpoint が VM サブネットに無い"),
            ("C", "Bastion が停止している"),
            ("D", "VM サイズが B1s だから"),
        ],
        ["B"],
        "ファイアウォールを閉じたら、VNet 統合（サービスエンドポイントか PE）が無いと VM からも拒否される。Bastion は管理プレーン。",
        ["Configure Azure Storage firewalls and virtual networks"],
    ),
    q(
        "C05", 24, "compute",
        "既存の ARM テンプレートを Bicep にしたい。公式の手順として正しいのはどれか。",
        [
            ("A", "ポータルの VM サイズ変更画面から自動変換される"),
            ("B", "ARM JSON を Bicep にデコンパイル（az bicep decompile 等）し、差分を見て直す"),
            ("C", "NSG をエクスポートすると Bicep になるので VM は手で書く"),
            ("D", "テンプレートの変換は AZ-305 の範囲で AZ-104 ではしない"),
        ],
        ["B"],
        "AZ-104 は ARM/Bicep の解釈・修正・デコンパイルが範囲。",
        ["Export a deployment as an Azure Resource Manager template or convert to Bicep"],
    ),
    q(
        "E05", 25, "monitor",
        "バックアップが 3 日連続で失敗していることに、ディスクが壊れてから気づいた。先に入れるべき監視はどれか。該当するものを2つ選べ。",
        [
            ("A", "Recovery Services / Backup の失敗アラート"),
            ("B", "VM のハートビート欠落アラート"),
            ("C", "パブリック IP を付けてインターネットから死活確認する"),
            ("D", "ゲストの Entra ロールを Viewer にする"),
            ("E", "Advisor のパフォーマンス推奨だけを見る"),
        ],
        ["A", "B"],
        "バックアップ失敗と VM 死は別シグナル。パブリック IP は監視の代わりにならない。Advisor は推奨であり失敗の即時検知ではない。",
        ["Configure and interpret reports and alerts for backups"],
    ),
    q(
        "A06", 26, "identity",
        "自分はサブスクリプション Reader、rg-pachislot-prod では Contributor。ストレージアカウントのアクセスキーをローテーションできるか。",
        [
            ("A", "できない。サブスクリプション Reader が常に勝つ"),
            ("B", "できる。リソースグループの Contributor が、その RG 内では勝つ"),
            ("C", "できるが Key Vault の権限が別途必須"),
            ("D", "できない。キー操作は Owner 専用"),
        ],
        ["B"],
        "RBAC は狭いスコープの許可が、そのスコープでは有効。Contributor はアクセスキーのローテーションができる。「サブスク Reader が常に勝つ」は誤り。",
        ["Interpret access assignments"],
    ),
    q(
        "D06", 27, "network",
        "自分 1 人が HTTPS でアプリを使う。2 台の VM を負荷分散する必要はいま無い。試験で「内部負荷分散」が正解になるのはどの要件か。",
        [
            ("A", "自宅ブラウザから直接 VIP にアクセスしたい"),
            ("B", "同一 VNet 内の別サブネット（例: 取得用コンテナ）からだけ Flask に振りたい。インターネットには出したくない"),
            ("C", "Cloudflare の代わりに必ず Public Load Balancer が要る"),
            ("D", "Bastion は内部 LB の背面に置く必要がある"),
        ],
        ["B"],
        "内部 LB は VNet 内部用。自宅ブラウザ向けは Public LB / App Gateway。設問は内部 LB が正解になる要件を聞いている。",
        ["Configure an internal or public load balancer"],
    ),
    q(
        "B06", 28, "storage",
        "アカウントキーが Git に混入した（app_settings 相当の事故）。最初にやる順として正しいのはどれか。",
        [
            ("A", "リポジトリを private にする → 何もしない"),
            ("B", "キーをローテーション → アプリの参照を Managed ID か SAS に切り替え → Git 履歴から除去"),
            ("C", "ソフトデリートを無効化する"),
            ("D", "ストレージを Archive にして読めなくする"),
        ],
        ["B"],
        "漏れた鍵は無効化が先。private 化だけでは clone 済みキーは生きる。",
        ["Manage access keys"],
    ),
    q(
        "C06", 29, "compute",
        "次の Bicep 断片の意図として正しいものはどれか。",
        [
            ("A", "Bastion からの SSH もすべて拒否する"),
            ("B", "インターネットからの 22 番を拒否する。Bastion サブネットからの管理は別ルール／別経路で残せる"),
            ("C", "Flask の 5000 番を公開する"),
            ("D", "送信の 443 を拒否する"),
        ],
        ["B"],
        "sourceAddressPrefix が Internet の Deny 22。Bastion は別サブネット・別経路。5000 も送信 443 も書いていない。",
        ["Interpret an Azure Resource Manager template or a Bicep file"],
        code=BICEP_C06,
    ),
    q(
        "E06", 30, "monitor",
        "KQL で「取得ジョブが Traceback を出した時間」を Log Analytics から探す。テーブル名のイメージとして適切なのはどれか。",
        [
            ("A", "Syslog または VM の Heartbeat だけを見て Traceback が必ず入る"),
            ("B", "エージェントで収集した Syslog / Heartbeat に加え、カスタムテーブルか ContainerLog（ジョブをコンテナに出した場合）。TimeGenerated と文字列で絞り込む"),
            ("C", "NSG フローログに Python の例外全文が入る"),
            ("D", "Budget クエリ"),
        ],
        ["B"],
        "例外本文はフローログには入らない。ログ収集を入れてから KQL。Heartbeat は生きているか用。",
        ["Query and analyze logs in Azure Monitor"],
    ),
    q(
        "B07", 31, "storage",
        "東日本リージョンが半日落ちても、昨日の pachislot.db バックアップだけは別リージョンから読みたい。オブジェクトレプリケーションや冗長で適切なのはどれか。",
        [
            ("A", "LRS"),
            ("B", "ZRS（同一リージョン 3 ゾーン）"),
            ("C", "GRS または GZRS"),
            ("D", "Premium LRS"),
        ],
        ["C"],
        "別リージョンから読む = GRS/GZRS。ZRS は同一リージョンのゾーン。",
        ["Configure Azure Storage redundancy"],
    ),
    q(
        "C07", 32, "compute",
        "データディスクが 30 GB のまま、venv とバックアップで逼迫してきた。VM を停止せず容量だけ増やしたい。",
        [
            ("A", "OS ディスクを交換する"),
            ("B", "データディスクをポータル／CLI でリサイズし、OS 上でパーティションを伸ばす"),
            ("C", "Blob に SQLite をコピーしてディスクを消す"),
            ("D", "Scale Set に入れないとディスクは伸ばせない"),
        ],
        ["B"],
        "マネージドディスクのリサイズは定番操作。OS 上のファイルシステム拡張を忘れない。",
        ["Manage virtual machine disks"],
    ),
    q(
        "A07", 0, "identity",
        "自分のアカウントがロックされた。SSPR はまだ有効にしていない。管理者が取るべき対応はどれか。該当するものを2つ選べ。",
        [
            ("A", "Entra 管理者がパスワードをリセットして入れるようにする"),
            ("B", "再発防止として SSPR を有効化する"),
            ("C", "所有者アカウントのパスワードを LINE で共有する"),
            ("D", "NSG で 22 番を Internet に Allow する"),
        ],
        ["A", "B"],
        "今すぐ入るには管理者によるリセット。次からは SSPR。パスワード共有も 22 番公開も試験でも実務でも不可。",
        ["Configure self-service password reset (SSPR)"],
    ),
    q(
        "D07", 0, "network",
        "実効セキュリティ規則を見ると、Flask の 5000 がまだ Allow になっている。Deny SSH（優先度 100）はある。理由としてあり得るのはどれか。該当するものを2つ選べ。",
        [
            ("A", "5000 の明示 Allow が、既定の DenyAll より優先度が高い（数値が小さい）"),
            ("B", "Application Security Group の関連付けで、その NIC に 5000 Allow が当たっている"),
            ("C", "Deny SSH は 22 番だけなので 5000 も閉じる"),
            ("D", "Bastion は常に 5000 をインターネットへ公開する"),
        ],
        ["A", "B"],
        "同じ方向では数値の小さいルールが勝つ。Deny 22 は 5000 に及ばない。ASG 経由の Allow も実効規則に出る。",
        ["Evaluate effective security rules in NSGs"],
    ),
    q(
        "B08", 0, "storage",
        "hall_daily_data の Parquet を大量に Databricks 学習用へコピーしたい。一方、コンテナにファイルが 3 つあるかだけポータルで確認したい。使い分けはどれか。",
        [
            ("A", "大量コピーは AzCopy、少数の確認は Storage Explorer かポータル"),
            ("B", "常に Storage Explorer の GUI が最速なので AzCopy は使わない"),
            ("C", "AzCopy は Linux 専用で macOS の学習マシンでは使えない"),
            ("D", "どちらもアカウントキーが無いと SAS でも動かない"),
        ],
        ["A"],
        "一括は AzCopy、目視確認は Explorer。AzCopy は Windows/macOS/Linux がある。認証はキー以外に SAS や ID もある。",
        ["Manage data by using Azure Storage Explorer and AzCopy"],
    ),
    q(
        "C08", 0, "compute",
        "vm-pachislot を rg-pachislot-prod から rg-pachislot-dr へ移したい。正しい説明はどれか。該当するものを2つ選べ。",
        [
            ("A", "VM と紐づく NIC・ディスクなど、依存リソースの移動可否を先に確認する"),
            ("B", "別リージョンへ移す操作は、リソースグループ移動ではなく再作成や Site Recovery の話になる"),
            ("C", "Bastion を削除しないと、同じリージョンの RG 間でも移せない"),
            ("D", "移動すると SQLite が自動で GRS の Blob になる"),
        ],
        ["A", "B"],
        "同一リージョンの RG 移動は依存関係付き。リージョン越えは Move ではない。Bastion 削除は必須ではない。ディスク上の DB はストレージ冗長に変わらない。",
        ["Move a virtual machine to another resource group, subscription, or region"],
    ),
    q(
        "A08", 0, "identity",
        "課金分析のため、全リソースにタグ app=pachislot と env=prod を付けたい。手動を忘れたくない。強制する手段はどれか。",
        [
            ("A", "思い出したときにポータルで付ける"),
            ("B", "Azure Policy で必須タグ（Deny または追加）を割り当てる"),
            ("C", "NSG ルール名を tag-prod にする"),
            ("D", "Blob のライフサイクルにタグを書く"),
        ],
        ["B"],
        "タグの強制は Policy。手動は忘れる。NSG 名もライフサイクルもタグガバナンスではない。",
        ["Apply and manage tags on resources", "Implement and manage Azure Policy"],
    ),
    q(
        "D08", 0, "network",
        "取得用サブネットに UDR を足し、0.0.0.0/0 の次ホップを None（破棄）にしてしまった。23:00 のホール取得が全滅する。原因はどれか。",
        [
            ("A", "取得元サイトへの送信 443 が捨てられる。UDR を Internet か Firewall に戻す"),
            ("B", "受信 NSG の Deny 22 が原因"),
            ("C", "Blob のソフトデリートが取得 HTTP を止める"),
            ("D", "自分の Reader ロールが原因で VM が名前解決できない"),
        ],
        ["A"],
        "UDR の Discard は送信を落とす。夜稼働データなしのインフラ原因になり得る。SSH Deny やソフトデリートとは別。",
        ["Configure user-defined routes", "Troubleshoot network connectivity"],
    ),
    q(
        "B09", 0, "storage",
        "90 日超のホール日次ダンプは Archive にある。今夜の夜稼働前にその日の島データを読みたい。必要なことはどれか。該当するものを2つ選べ。",
        [
            ("A", "対象 Blob を Hot または Cool へ再hydrate する"),
            ("B", "再hydrate の完了を待ってから読む。Archive のままでは間に合わない"),
            ("C", "Archive のまま AzCopy すれば即読める"),
            ("D", "VM を D シリーズに上げれば Archive をメモリに展開できる"),
        ],
        ["A", "B"],
        "Archive は再hydrate が要る。夜稼働の直前に触るデータは Archive に置かない、がこのアプリの実務でも同じ。",
        ["Configure storage tiers"],
    ),
    q(
        "C09", 0, "compute",
        "データディスク上の records（個人収支）を、ホストのキャッシュからも守りたい。AZ-104 の範囲で足すのはどれか。",
        [
            ("A", "VM の encryption at host を有効化する"),
            ("B", "NSG で受信 443 を閉じる"),
            ("C", "サブスクリプションを Reader だけにする"),
            ("D", "バックアップコンテナを Cool にする"),
        ],
        ["A"],
        "Encryption at host がホストキャッシュを含むディスク暗号化の話。NSG や RBAC、Cool 層とは別レイヤ。",
        ["Configure encryption at host for Azure virtual machines"],
    ),
    q(
        "A09", 0, "identity",
        "rg-pachislot-prod に CanNotDelete ロックがある。vm-pachislot を rg-pachislot-dr へ移そうとしたら失敗した。最初に疑うのはどれか。",
        [
            ("A", "ロックを外すか、移動をブロックしないスコープにする。移動できないリソース種別も確認する"),
            ("B", "ロックは移動を妨げない。Availability Set 不足が原因"),
            ("C", "Archive 層の Blob が VM 移動を止める"),
            ("D", "Bastion が 2 台無いと RG 移動はできない"),
        ],
        ["A"],
        "削除ロックは移動・削除系の操作を止めることがある。種別によってはそもそも Move 非対応。セットや Bastion 台数の話ではない。",
        ["Configure resource locks", "Manage resource groups"],
    ),
    q(
        "D09", 0, "network",
        "vnet-dbx の Databricks から、vnet-pachislot 側 Private Endpoint の Blob を名前で引きたい。ピアリングは済んでいる。まだ NXDOMAIN になる。必要なことはどれか。該当するものを2つ選べ。",
        [
            ("A", "privatelink.blob.core.windows.net の Private DNS ゾーンを用意する"),
            ("B", "ピアリング先の vnet-dbx にもそのゾーンをリンクする"),
            ("C", "vm-pachislot にパブリック IP を付ける"),
            ("D", "ストレージを GRS にする"),
        ],
        ["A", "B"],
        "PE の名前解決は Private DNS。ピアリングだけではゾーンリンクは増えない。パブリック IP も GRS も DNS の代わりにならない。",
        ["Configure Azure DNS", "Configure private endpoints for Azure PaaS"],
    ),
    q(
        "B10", 0, "storage",
        "設定ファイルだけを SMB で共有し、認証はアカウントキーではなく ID にしたい。正本 SQLite の置き場は変えたくない。正しい組みはどれか。該当するものを2つ選べ。",
        [
            ("A", "設定ファイル共有に Azure Files と ID ベースアクセスを使う"),
            ("B", "pachislot.db はデータディスクのままにする"),
            ("C", "WAL 付き SQLite を Azure Files に置いて複数プロセスで開く"),
            ("D", "ストレージアカウントキーを Flask に直書きする"),
        ],
        ["A", "B"],
        "Files + ID は設定共有向き。このアプリの SQLite はロックと遅延で Files に向かない。キー直書きは B06 の事故の再現。",
        ["Configure identity-based access for Azure Files"],
    ),
    q(
        "C10", 0, "compute",
        "Web 用 VM と取得用 VM の 2 台にした。計画メンテナンス時に同時に落ちないよう、更新ドメインを分けたい。ゾーン分散は必須ではない。どれか。",
        [
            ("A", "同一リージョンの Availability Set に 2 台を入れる"),
            ("B", "1 台だけ Availability Zone に置けば更新ドメインも分かれる"),
            ("C", "Virtual Machine Scale Set を min=10 にする"),
            ("D", "両方を同じ障害ドメインに固定する"),
        ],
        ["A"],
        "更新ドメインはセットの話。ゾーンはデータセンター障害用で、1 台では更新ドメイン分散にならない。10 台は過剰。",
        ["Deploy virtual machines to availability zones and availability sets"],
    ),
    q(
        "A10", 0, "identity",
        "自分はサブスクリプション Reader。ストレージアカウント stpapachislot だけ Owner。実効権限として正しいのはどれか。",
        [
            ("A", "そのストレージのアクセスキーは回せるが、VM を削除する権限までは持たない"),
            ("B", "サブスク Reader が常に勝つのでキーも回せない"),
            ("C", "ストレージ Owner なのでサブスクリプション全体の Owner と同じ"),
            ("D", "VM のディスクをデタッチできる"),
        ],
        ["A"],
        "狭いスコープの Owner はそのリソースに効く。サブスク Reader がキー操作を打ち消すわけではない。VM には及ばない。",
        ["Interpret access assignments", "Assign roles at different scopes"],
    ),
    q(
        "D10", 0, "network",
        "Bastion と Standard SKU のロードバランサーを使う予定がある。パブリック IP の SKU で適切なのはどれか。",
        [
            ("A", "Standard パブリック IP。Basic は制限が多く、Bastion や Standard LB と組み合わせない"),
            ("B", "Basic の方がゾーン冗長なので Bastion には Basic を付ける"),
            ("C", "Bastion を使うなら VM 自身にパブリック IP が必須"),
            ("D", "Standard パブリック IP は HTTP 専用で HTTPS の取得には使えない"),
        ],
        ["A"],
        "Bastion / Standard LB は Standard IP。VM にパブリック IP を付ける必要はない（この演習の前提でも付けない）。",
        ["Configure public IP addresses", "Implement Azure Bastion"],
    ),
    q(
        "B11", 0, "storage",
        "stpapachislot の暗号化。個人の学習用バックアップで、鍵を自分の HSM で回す規制はまだ無い。どれが適切か。",
        [
            ("A", "既定の Microsoft マネージドキーで足りる。鍵の管理主体が監査要件になるときだけカスタマーマネージドキー"),
            ("B", "CMK が無いと Blob は平文で置かれる"),
            ("C", "MMK は無効化できないので必ず CMK にする"),
            ("D", "暗号化は NSG の TLS 検査で行う"),
        ],
        ["A"],
        "ストレージは既定で暗号化済み（MMK）。CMK はコンプライアンス要件。NSG はネットワーク。",
        ["Configure storage account encryption"],
    ),
    q(
        "C11", 0, "compute",
        "Flask だけ App Service に出し、正本 SQLite は今の VM ディスクに残す提案。判断として正しいのはどれか。",
        [
            ("A", "あり得る。App Service のローカルディスクに pachislot.db を置かないことが条件"),
            ("B", "App Service に db ファイルを置けばスケールアウトしても自動共有される"),
            ("C", "App Service は Python を実行できないので分割できない"),
            ("D", "分割すると Bastion が使えなくなり SSH を世界公開するしかない"),
        ],
        ["A"],
        "コードと正本を分けるのは試験でも実務でも筋が通る。揮発ディスクに SQLite を置くのが失敗パターン。Python も Bastion も分割の禁止理由ではない。",
        ["Create and configure Azure App Service"],
    ),
    q(
        "A11", 0, "identity",
        "rg-pachislot-prod の Contributor では、同僚に Reader を付けられなかった。ロールを他人に割り当てられるのはどれか。該当するものを2つ選べ。",
        [
            ("A", "Owner"),
            ("B", "User Access Administrator"),
            ("C", "Reader"),
            ("D", "Backup Reader"),
        ],
        ["A", "B"],
        "Contributor はリソース操作はできるが RBAC 付与はできない。付与は Owner か User Access Administrator。",
        ["Manage built-in Azure roles"],
    ),
    q(
        "D11", 0, "network",
        "Connection Monitor で vm-pachislot → 取得元サイトの HTTPS が失敗する。受信 NSG で 5000 は Deny のまま。最初に見るのはどれか。",
        [
            ("A", "送信 NSG と名前解決（DNS）。受信 5000 は取得の出に関係ない"),
            ("B", "受信 22 の Deny を Allow に変える"),
            ("C", "Availability Set の障害ドメイン"),
            ("D", "バックアップコンテナの Archive 設定"),
        ],
        ["A"],
        "取得は VM から外へ出る通信。受信 5000 や SSH、セット、Archive は別問題。",
        ["Use Azure Network Watcher and Connection monitor"],
    ),
    q(
        "C12", 0, "compute",
        "App Service で Flask を公開するとき、AZ-104 でよくセットになる設定はどれか。該当するものを2つ選べ。",
        [
            ("A", "カスタム DNS 名に TLS 証明書をバインドする"),
            ("B", "デプロイスロットはコード入れ替え用。本番スロットに pachislot.db を置かない"),
            ("C", "スロットを使うと NSG が不要になり 22 番が自動で開く"),
            ("D", "カスタムドメインは Standard パブリック LB 専用で App Service には使えない"),
        ],
        ["A", "B"],
        "カスタムドメイン + TLS とスロットは App Service の定番。スロットは SSH 公開ではない。App Service 自体がカスタムドメインを持つ。",
        ["Configure certificates and TLS for an App Service", "Configure deployment slots for an App Service"],
    ),
    q(
        "A12", 0, "identity",
        "いまサブスクリプションは個人の従量課金が 1 つ。管理グループは今すぐ要るか。",
        [
            ("A", "今は不要。複数サブスクや環境（dev/prod）を分けてからでよい"),
            ("B", "1 台の VM でも管理グループが無いと Policy は効かない"),
            ("C", "Bastion の前提条件である"),
            ("D", "SQLite のバックアップ先として必須である"),
        ],
        ["A"],
        "管理グループは大規模ガバナンス用。Policy はサブスクや RG にも付けられる。Bastion や DB の前提ではない。",
        ["Configure management groups"],
    ),
    q(
        "C13", 0, "compute",
        "取得用 Playwright イメージをレジストリに置き、ポータルから短時間だけコンテナを上げたい。手順として正しいものはどれか。該当するものを2つ選べ。",
        [
            ("A", "Azure Container Registry にイメージを置く"),
            ("B", "ACI または Container Apps が ACR から pull するよう認証を設定する"),
            ("C", "毎回 Bastion 上で docker build しないと ACI は動かない"),
            ("D", "ACR は匿名 pull が試験の推奨である"),
        ],
        ["A", "B"],
        "ACR → ACI/Container Apps がポータル範囲の定番。Bastion で毎回ビルドは不要。匿名公開は推奨しない。",
        ["Create and manage an Azure Container Registry", "Provision a container by using Azure Container Instances"],
    ),
    q(
        "A13", 0, "identity",
        "「VM にパブリック IP を付けるデプロイを禁止したい」。Policy の効果 Audit と Deny の違いはどれか。",
        [
            ("A", "Audit は作れて警告だけ残る。作成そのものを止めるなら Deny"),
            ("B", "Audit は作成をブロックし、Deny はログだけ"),
            ("C", "どちらもタグを付けるだけで、作成は止められない"),
            ("D", "Deny はサブスクリプション Owner には効かない"),
        ],
        ["A"],
        "禁止したい操作は Deny。Audit はコンプライアンス確認用。Owner でも Deny は効く（例外は別途除外）。",
        ["Implement and manage Azure Policy"],
    ),
    q(
        "C14", 0, "compute",
        "いまの VM をポータルからテンプレートに落とし、SKU だけ B1s から B2s に変えて同じ構成を出したい。手順として正しいのはどれか。",
        [
            ("A", "デプロイを ARM としてエクスポートし、Bicep にデコンパイルして SKU を直して再デプロイする"),
            ("B", "VM サイズ変更画面が Bicep ファイルを自動生成するので、それを保存するだけ"),
            ("C", "AZ-104 ではテンプレートを触らず、ポータル操作だけが範囲である"),
            ("D", "NSG の JSON をストレージアカウントに貼れば VM SKU が変わる"),
        ],
        ["A"],
        "エクスポートとデコンパイル、パラメータ修正は AZ-104 の範囲。サイズ変更 UI は既存 VM の操作で、テンプレート生成ではない。",
        ["Export a deployment as an ARM template or convert to Bicep"],
    ),
    q(
        "A14", 0, "identity",
        "監査法人の同僚をゲスト招待した。ライセンスと RBAC の関係として正しいものはどれか。該当するものを2つ選べ。",
        [
            ("A", "ポータルで Reader としてメトリックを見る、は RBAC 割り当てで足りることが多い"),
            ("B", "条件付きアクセスなど Entra の有料機能は、テナント側のライセンスが別途要ることがある"),
            ("C", "ゲストは Premium ライセンスが無いとログイン自体できない"),
            ("D", "ゲストは自動で VM のローカル管理者になる"),
        ],
        ["A", "B"],
        "ゲスト招待 + RBAC が基本。全機能が無償とは限らないが、ログイン不能になるわけでもない。ローカル管理者は別設定。",
        ["Manage external users", "Manage licenses in Microsoft Entra ID"],
    ),
    q(
        "S01", 0, "monitor",
        "最初に切り分ける順番として最も妥当なのはどれか。",
        [
            ("A", "すぐ西日本へ Site Recovery"),
            ("B", "VM が動いているか（メトリック / Heartbeat）→ 送信が NSG で落ちていないか（Network Watcher）→ ストレージへバックアップが書けているか"),
            ("C", "NSG で 5000 を全面 Allow"),
            ("D", "ディスクを 4 TB に拡張"),
        ],
        ["B"],
        "死活 → 経路 → データの順。いきなり ASR しない。",
        ["Interpret metrics in Azure Monitor"],
        preamble=CASE_PREAMBLE,
    ),
    q(
        "S02", 0, "monitor",
        "Heartbeat は来ている。IP フロー検証で Internet 向け 443 が NSG Deny。原因としてあり得るのはどれか。",
        [
            ("A", "Bastion が 443 を占有している"),
            ("B", "送信ルールで Internet を Deny したか、Application Security Group の関連付けを間違えた"),
            ("C", "Blob のソフトデリート"),
            ("D", "Reader ロールしかない"),
        ],
        ["B"],
        "送信 Deny。Bastion は inbound 管理。",
        ["Troubleshoot network connectivity"],
    ),
    q(
        "S03", 0, "monitor",
        "取得は復旧した。昨日の不完全な hall_daily_data を、バックアップの「取得前」に戻したい。アプリの Flask は動いたまま、データディスクだけ戻す。",
        [
            ("A", "VM 全体を別リージョンにフェールオーバー"),
            ("B", "Backup からディスクを復元し、既存 VM にスワップ／再アタッチする手順を取る（本番前にロックとスナップショットを確認）"),
            ("C", "Parquet の SAS を再発行する"),
            ("D", "Container Apps のレプリカを 10 にする"),
        ],
        ["B"],
        "データディスクだけ戻すのが Backup の使い方。Flask を西日本に飛ばす話ではない。",
        ["Perform backup and restore operations by using Azure Backup"],
    ),
    q(
        "S04", 0, "monitor",
        "再発時にスマホへ通知したい。CPU アラートは 23:00 で鳴るので使いたくない。必要なものはどれか。該当するものを2つ選べ。",
        [
            ("A", "CPU > 10% を 1 分間隔のメトリックアラート"),
            ("B", "カスタムログに「取得失敗」が出たときのログアラート"),
            ("C", "アクション グループ（メール / SMS / Webhook）"),
            ("D", "ディスク IOPS の情報アラートだけ"),
            ("E", "Policy の監査効果のみ"),
        ],
        ["B", "C"],
        "業務失敗はログで取り、通知はアクション グループ。CPU は 23:00 の正常負荷と区別できない。",
        ["Set up alert rules, action groups, and alert processing rules"],
    ),
]


def validate(questions: list[dict]) -> None:
    ids = [item["id"] for item in questions]
    assert len(questions) == 60, len(questions)
    assert len(set(ids)) == 60
    by_domain = {}
    multi = 0
    for item in questions:
        keys = {c["key"] for c in item["choices"]}
        assert len(item["choices"]) in (4, 5)
        assert 1 <= item["select_count"] <= 3
        assert len(item["answer"]) == item["select_count"]
        assert set(item["answer"]).issubset(keys)
        assert "正解は" not in item["stem"]
        by_domain[item["domain"]] = by_domain.get(item["domain"], 0) + 1
        if item["select_count"] > 1:
            multi += 1
    assert by_domain == {
        "identity": 14,
        "storage": 11,
        "compute": 14,
        "network": 11,
        "monitor": 10,
    }, by_domain
    assert 9 <= multi <= 15, multi


def main() -> None:
    for i, item in enumerate(QUESTIONS, 1):
        item["no"] = i
    validate(QUESTIONS)
    payload = {
        "id": "set01",
        "title": "パチスロ収支基盤セット1",
        "exam": "AZ-104",
        "status": "complete",
        "planned_count": 60,
        "time_limit_min": 100,
        "pass_percent": 70,
        "case_study": (
            "リソースグループ rg-pachislot-prod（東日本）。VM vm-pachislot に Flask と "
            "SQLite 正本。データディスク disk-pachislot-data。ストレージ stpapachislot。"
            "VNet は snet-app / AzureBastionSubnet / snet-pe。"
            "パブリック IP を VM に付けない。23:00〜翌 4:00 は取得と Gemini で CPU が占有される。"
        ),
        "questions": QUESTIONS,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(QUESTIONS)} questions)")


if __name__ == "__main__":
    main()
