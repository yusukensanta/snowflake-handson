# 01 · セットアップとガードレール

**English:** [../../guides/01-setup-and-guardrails.md](../../guides/01-setup-and-guardrails.md)

順序が重要です: ツール → 接続 → preflight → ガードレール(リソースモニター) → コンピュートを使う作業。

## 1. ツールのインストール
```bash
scripts/install-tools --dry-run   # 実行計画を確認
scripts/install-tools             # terraform, snow (SnowCLI), shellcheck, gitleaks。再実行しても安全
```

## 2. 管理者接続の作成(人間ユーザー、MFA)
1. トライアルのユーザーで Snowsight にサインインし、MFA を有効にします(プロフィール > Authentication)。
2. `config/connections.toml.example` を `~/.snowflake/connections.toml` にコピーし、`<org>-<account>` とユーザー名を記入して `chmod 600` します。
3. `snow connection test -c handson_admin` が `Status OK` を表示すれば成功です。

実ファイルはリポジトリ外にあり、git の管理対象外です。**クラウドとの対応:** `aws sso login` のプロファイルに相当し、Terraform 用のサービス ID(ガイド 02)はワークロード用 IAM ロールに相当します。

## 3. preflight の実行
```bash
scripts/preflight --dry-run
scripts/preflight
```
ツール、接続、リージョン、エディション、Cortex のクロスリージョン設定(読み取りのみで変更しません)、Snowflake 管理ストレージでの Iceberg の可否(一時テーブルを作成して削除)を確認し、Snowsight(Admin > Cost Management)に表示される実際のクレジット単価の入力を求めます。

| 結果 | 意味 | 代替策 |
|---|---|---|
| edition が `block` | ポリシーには Enterprise が必要 | Enterprise のトライアルを使う |
| iceberg が `warn` | Snowflake ストレージが使えない | Iceberg は概念説明と付録のみにする |
| cortex が `warn` | CoCo/Cortex が使えない可能性 | AI ラボをスキップし、リージョン内にとどまる(クロスリージョン推論は使わない) |

**確認結果(記入、アカウント ID は伏せる):** リージョン ___、エディション ___、単価 ___、Iceberg プローブ ___、Cortex ___。

## このステップのコスト
約 0.1 クレジット(プローブ用に XS ウェアハウスを数秒使用)。

## 確認
`scripts/preflight` が終了コード 0 で終わり、`block` の行が出ないこと。

## 4. ワークロードの前にガードレール
```bash
scripts/bootstrap --dry-run      # 実行される SQL をすべて表示(何も実行しない)
scripts/bootstrap --quota 80     # アカウントのリソースモニター、TF_ADMIN ロール、TERRAFORM サービスユーザーと鍵ペア
scripts/cost-guard --status
```
- **アカウントのリソースモニター** `HANDSON_ACCOUNT_MONITOR`: 上限 80 クレジット、50/75/90 % で通知、95 % でサスペンド、100 % で `SUSPEND_IMMEDIATE`。設定には `ACCOUNTADMIN` が必要なので、Terraform ではなくスクリプトが作成します。
- **88 ではなく 80 にする理由:** $4.50/クレジットなら $400 は約 88 クレジットです。差分は、モニターが作動した後に課金されるクレジットに対する安全マージンです。実際の単価で再計算し、約 10 % を引いてください。
- **サービス ID:** ユーザー `TERRAFORM`(`TYPE = SERVICE`、鍵ペアのみ、パスワードなし)とロール `TF_ADMIN`。Terraform に必要なアカウント権限だけを持ちます。秘密鍵は入力したパスフレーズで暗号化され、`~/.snowflake/` に置かれ、リポジトリには入りません。Terraform 実行時はシェルで `PRIVATE_KEY_PASSPHRASE` を export します。
- **ウェアハウスのモニター**(Terraform の `finops` モジュール): ウェアハウスごとに 1 つ。75/90 % で通知、100 % でサスペンド。
- **緊急停止:** `scripts/cost-guard --suspend-all`。

クラウドとの対応: リソースモニターは AWS Budgets のアクションや GCP の予算+Pub/Sub による停止に近いですが、プラットフォーム自身が強制します。

## このステップのコスト(続き)
0 クレジット。モニターとロールはメタデータのみです。

## 確認(ガードレール)
`scripts/cost-guard --status` に、上限 80 の `HANDSON_ACCOUNT_MONITOR` が表示されること。
