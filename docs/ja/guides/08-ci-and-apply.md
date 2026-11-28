# 08 · CI と GitHub Actions からの apply

<!-- nav:top -->
[🏠 7日間の流れ](../../../README.ja.md#7日間の流れ) · ← [07 監視と FinOps](07-monitoring-finops-teardown.md) · [付録 AWS](appendix-aws.md) →
<!-- /nav:top -->

**English:** [../../guides/08-ci-and-apply.md](../../guides/08-ci-and-apply.md)

業務上のルール: **plan はどこでも、apply は人間が承認した後に CI からのみ。** 最初の apply(ガイド 02)はアカウントのブートストラップのためローカルから行い、CI を設定した後はこのフローに切り替えます。

> **開始前に確認(2026-11-28):** HashiCorp は未解決の障害 [Temporary limitations for users on Free Subscription](https://status.hashicorp.com/incidents/01M7XJY4CWY8VQHDC8WFQKEZ47) を公表しており、無料の組織を新規作成できません(`Free tier organizations created by user limit reached`)。HCP Terraform の組織がない場合は、[ステータスページ](https://status.hashicorp.com)を確認するか、[HashiCorp サポート](https://www.hashicorp.com/support)に連絡してください。このガイドは任意です。パイプラインはこのガイドなしで動作するため、後片付け([ガイド 07](07-monitoring-finops-teardown.md))に進めます。HCP ポータル(`portal.cloud.hashicorp.com`)の組織だけでは、Terraform から見えない場合があります。

## ワークフロー
| ファイル | 実行タイミング | 内容 |
|---|---|---|
| `.github/workflows/ci.yml` | すべての PR と `main` への push | `ruff`、`ty`、`pytest`(カバレッジ 80% 以上)、`shellcheck`、`scripts/check-secrets`、`terraform fmt` + `validate`(認証情報は不要) |
| `.github/workflows/terraform.yml` | `terraform/**` を変更する PR と push | PR: `plan`(ジョブのサマリーに表示)。`main`: `plan` の後、`snowflake-apply` 環境の承認を経て **`apply`** |

アクションはコミット SHA で固定し、権限は `contents: read` のみです。plan ファイルはアーティファクトとしてアップロードしません(公開リポジトリのアーティファクトは誰でも取得でき、plan にはシークレットが含まれうるため)。フォークからの PR にシークレットは渡されません。

## 初回セットアップ
### 手順 1: 共有ステート
ローカルの plan と CI の apply は同じステートを使う必要があるため、ステート保管専用(*Execution mode* **Local**)の無料の HCP Terraform ワークスペースに移します。以下の手順は Terraform 1.17.2 と HashiCorp のドキュメントに基づきますが、**通しでは実行していません**(上の注意を参照)。リポジトリのルートで、同じシェルで実行し、失敗したらそこで止めてください。

**1a. ローカルステートのままで基準の確認とバックアップ:**
```bash
read -rs PRIVATE_KEY_PASSPHRASE && export PRIVATE_KEY_PASSPHRASE      # パスフレーズを入力して Enter
source scripts/tf-env
terraform -chdir=terraform/envs/handson init
terraform -chdir=terraform/envs/handson plan                          # No changes になること
terraform -chdir=terraform/envs/handson state list | wc -l            # この件数を控える
cp terraform/envs/handson/terraform.tfstate ~/.snowflake/pre-hcp.tfstate
chmod 600 ~/.snowflake/pre-hcp.tfstate                                # ステートはシークレットを含みうるのでリポジトリの外に置く
```

**1b. ワークスペースを作成して移行する。** [app.terraform.io](https://app.terraform.io) の組織が必要です。`-migrate-state` は使わないでください(HCP Terraform では Terraform が拒否します)。また `TF_WORKSPACE` ではワークスペースは作成されず、`Invalid workspace selection` で失敗します。git 管理対象外の `backend.tf` に `name` を書くと作成されます:
```bash
terraform login
export TF_CLOUD_ORGANIZATION="<your-org>"
export TF_CLOUD_PROJECT="<your-project>"                              # 任意。既定のプロジェクトなら省略
unset TF_WORKSPACE                                                    # TF_WORKSPACE は既存のワークスペースを選ぶだけ
cat > terraform/envs/handson/backend.tf <<'EOF'
terraform {
  cloud {
    workspaces {
      name = "snowflake-handson"
    }
  }
}
EOF
terraform -chdir=terraform/envs/handson init                          # ステート移行を聞かれたら yes。まだ plan しない
```

**1c. 新しいワークスペースを Local に切り替える。** [ワークスペース API](https://developer.hashicorp.com/terraform/cloud-docs/api-docs/workspaces) を使います(UI では *Settings > General > Execution Mode*)。`local` と表示されれば成功です:
```bash
token=$(python3 -c 'import json,pathlib; p=pathlib.Path.home()/".terraform.d/credentials.tfrc.json"; print(json.loads(p.read_text())["credentials"]["app.terraform.io"]["token"])')
printf 'header = "Authorization: Bearer %s"\n' "$token" | curl -sS --fail-with-body -K - \
  -X PATCH -H "Content-Type: application/vnd.api+json" \
  -d '{"data":{"type":"workspaces","attributes":{"execution-mode":"local","setting-overwrites":{"execution-mode":true}}}}' \
  "https://app.terraform.io/api/v2/organizations/$TF_CLOUD_ORGANIZATION/workspaces/snowflake-handson" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["data"]["attributes"]["execution-mode"])'
unset token
```

**1d. 確認:**
```bash
export TF_WORKSPACE=snowflake-handson                                 # CI と setup-github が使う名前
terraform -chdir=terraform/envs/handson state list | wc -l            # 移行前と同じ件数
terraform -chdir=terraform/envs/handson plan                          # No changes になること
```
件数が異なる場合や、plan がリソースを作成しようとする場合は、**apply しないでください**。CI は `backend.tf.example` の空の `cloud {}` ブロックを使い、`TF_WORKSPACE` でこのワークスペースを選びます。

**ローカルステートに戻す**(`init` が失敗し、何も移行していない場合。plan がすべてを作成しようとするなら apply しないでください。控えは `~/.snowflake/pre-hcp.tfstate` にあります):
```bash
rm -f terraform/envs/handson/backend.tf
unset TF_CLOUD_ORGANIZATION TF_CLOUD_PROJECT TF_WORKSPACE
source scripts/tf-env
terraform -chdir=terraform/envs/handson init -reconfigure
terraform -chdir=terraform/envs/handson plan                          # No changes になること
```

### 手順 2〜5
2. **CI 用の ID。** `TERRAFORM` ユーザーに CI 専用の 2 つ目の公開鍵を登録します(`ALTER USER TERRAFORM SET RSA_PUBLIC_KEY_2='…'`)。ノート PC の鍵とは独立してローテーションできます。
3. **GitHub Environments**(Settings > Environments): `snowflake-plan`(**必須レビュアー**を設定。ワークフローの変更を含む PR のコードは、あなたが内容を確認した後でのみ認証情報付きで実行されます)と `snowflake-apply`(**必須レビュアー**、デプロイ対象ブランチは `main` のみ)。シークレットは環境にだけ登録し、各ジョブは自分の環境のものだけを読みます。**`snowflake-plan` には別の読み取り専用の Snowflake ID**(別ユーザーと、リフレッシュに必要な範囲に絞ったロール)を使い、`TF_ADMIN` の鍵は `snowflake-apply` にだけ置きます。変数 `SNOWFLAKE_ROLE` は環境ごとに設定します。シークレット:
   `SNOWFLAKE_ORGANIZATION_NAME`、`SNOWFLAKE_ACCOUNT_NAME`、`SNOWFLAKE_USER`、`SNOWFLAKE_PRIVATE_KEY`、`SNOWFLAKE_PRIVATE_KEY_PASSPHRASE`、`TF_API_TOKEN`、`TFVARS_JSON`(非公開の tfvars を JSON にしたもの。設定があれば必須)。変数: `TF_CLOUD_ORGANIZATION`、`TF_WORKSPACE`。
   **このリポジトリは読み取り専用の plan 用 ID を作成しません**(後述の `TERRAFORM_PLAN` / `TF_PLAN` は名前の例です)。ユーザーと権限は自分で作成してください。使い捨てのトライアルアカウントでは、代わりに両方の環境へ `TERRAFORM`、`TF_ADMIN`、CI 用の鍵を設定することもできます。その場合、承認した PR の plan は管理者権限で実行されるため、承認前に差分をすべて読んでください。
4. **`main` のブランチ保護:** `ci` のチェックとプルリクエストを必須にします。
5. **ネットワークポリシー:** GitHub ホストランナーの IP は変動します。`enforce_account_policies = false` のままにしてください([ガイド 07](07-monitoring-finops-teardown.md) のセクション 2)。このフラグは `NP_HANDSON` をアカウント全体に適用するため、`TERRAFORM` と plan 用ユーザーもブロックされ、CI がサインインできなくなります。

## シークレットと変数の一覧
ワークフローが読み取るすべての値です。ここにある値は一切コミットしません。`scripts/setup-github`(後述)がすべて設定します。

| 名前 | 種類 | スコープ | 内容と入手方法 |
|---|---|---|---|
| `TF_CLOUD_ORGANIZATION` | 変数 | リポジトリ | HCP Terraform の組織名(app.terraform.io > Organizations) |
| `TF_WORKSPACE` | 変数 | リポジトリ | ステートを保管するワークスペース(*Execution mode = Local*) |
| `TF_API_TOKEN` | シークレット | 各環境 | plan と apply ができる HCP Terraform の API トークン。Free プランでは[追加のチームは利用不可とされている](https://developer.hashicorp.com/terraform/cloud-docs/overview)ため、有効期限を付けた[ユーザートークン](https://app.terraform.io/app/settings/tokens)を使います。このトークンはあなたの全権限を持ちます。有料プランでは、ワークスペースに限定したチームトークンを推奨します |
| `SNOWFLAKE_ORGANIZATION_NAME` | シークレット | 各環境 | `SELECT CURRENT_ORGANIZATION_NAME();` |
| `SNOWFLAKE_ACCOUNT_NAME` | シークレット | 各環境 | `SELECT CURRENT_ACCOUNT_NAME();`(URL 全体ではなく名前のみ) |
| `SNOWFLAKE_USER` | シークレット | 各環境 | apply は `TERRAFORM`。plan は別の読み取り専用ユーザー |
| `SNOWFLAKE_PRIVATE_KEY` | シークレット | 各環境 | そのユーザーの PEM 秘密鍵(下で生成)。改行は保持されます |
| `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE` | シークレット | 各環境 | 鍵のパスフレーズ。暗号化していない鍵なら省略(非推奨) |
| `SNOWFLAKE_ROLE` | 変数 | 各環境 | apply は `TF_ADMIN`。plan は読み取り専用ロール |
| `TFVARS_JSON` | シークレット | 各環境 | **非公開の `terraform.tfvars` に設定があれば必須**(後述)。同じ設定を JSON にしたもの |

アカウント情報を変数ではなくシークレットにしているのは意図的です。このリポジトリは公開されており、シークレットの値はログ上でマスクされます。

### 非公開の設定を CI に渡す
CI はまっさらなチェックアウトから始まり、git 管理対象外の `terraform.tfvars` を参照できません。省略した設定は既定値になるため、plan は列タグ(ガイド 04)やペルソナの権限付与を**削除**しようとします。`terraform.tfvars` のすべての設定を `~/.snowflake/tfvars.json` に書いてください(タグの対応表はワークフローが生成します)。例:
```json
{"apply_column_tags": true, "grant_personas_to_user": "<your Snowflake user>"}
```

### CI 専用の鍵ペアを生成する
```bash
openssl genrsa 2048 | openssl pkcs8 -topk8 -v2 aes-256-cbc -inform PEM -out ~/.snowflake/ci.p8      # パスフレーズを聞かれます
openssl rsa -in ~/.snowflake/ci.p8 -pubout -out ~/.snowflake/ci.pub
# 公開鍵は 2 つ目の鍵として登録します。ノート PC の鍵はそのまま使え、CI だけ単独でローテーションできます:
#   ALTER USER TERRAFORM SET RSA_PUBLIC_KEY_2='<ci.pub の BEGIN/END 行を除いた内容>';
```
plan には別の鍵(と別のユーザー)を使います。ローテーションは、新しい鍵を生成し、`RSA_PUBLIC_KEY_2` を設定し、`scripts/setup-github --execute` を再実行し、古い鍵を削除する、という順で行います。アップロード後、不要ならローカルの `.p8` ファイルは削除してください。

### 設定済みの内容を確認する(名前のみ。GitHub は値を表示しません)
```bash
gh variable list; gh variable list --env snowflake-apply
gh secret list --env snowflake-plan; gh secret list --env snowflake-apply
```

## スクリプトによるセットアップ(手順 3 と 4)
`scripts/setup-github` は、GitHub CLI を使って、必須レビュアー付きの 2 つの環境の作成、`snowflake-apply` の `main` への限定、変数とシークレットの登録、必要なら `main` のブランチ保護までを行います。冪等なので、シークレットのローテーションにも `--execute` を付けて再実行できます。リポジトリ管理者として `gh auth login` が必要です。
```bash
export TF_CLOUD_ORGANIZATION=… TF_WORKSPACE=… TF_API_TOKEN=…
export PLAN_SNOWFLAKE_USER=TERRAFORM_PLAN  PLAN_SNOWFLAKE_ROLE=TF_PLAN   PLAN_SNOWFLAKE_PRIVATE_KEY_FILE=~/.snowflake/plan.p8
export APPLY_SNOWFLAKE_USER=TERRAFORM      APPLY_SNOWFLAKE_ROLE=TF_ADMIN APPLY_SNOWFLAKE_PRIVATE_KEY_FILE=~/.snowflake/ci.p8
export SNOWFLAKE_ORGANIZATION_NAME=… SNOWFLAKE_ACCOUNT_NAME=…           # 両環境で共通
export TFVARS_JSON_FILE=~/.snowflake/tfvars.json    # 非公開の設定(上記)
# CI 用の鍵のパスフレーズ。指定しないと tf-env が export したノート PC 用が登録される
read -rs APPLY_SNOWFLAKE_PRIVATE_KEY_PASSPHRASE && export APPLY_SNOWFLAKE_PRIVATE_KEY_PASSPHRASE
read -rs PLAN_SNOWFLAKE_PRIVATE_KEY_PASSPHRASE && export PLAN_SNOWFLAKE_PRIVATE_KEY_PASSPHRASE
scripts/setup-github --branch-protection             # プレビュー(呼び出しのみ表示し、値は表示しません)
scripts/setup-github --execute --branch-protection
```
シークレットの値はシェルと鍵ファイルから読み込まれ、そのまま GitHub に送られます。スクリプトが値を表示したり保存したりすることはありません。既定ではセルフレビューを許可します(個人オーナー向け)。本当の 4-eyes 承認にするには、2 人目のレビュアーと `--prevent-self-review` を追加してください。結果は `gh api repos/OWNER/REPO/environments --jq '.environments[].name'` で確認できます。

## 日常のフロー
```bash
export TF_CLOUD_ORGANIZATION=… TF_WORKSPACE=…
terraform -chdir=terraform/envs/handson plan      # ローカル。共有ステートに対して読み取りのみ
git switch -c change-x && git commit … && gh pr create
# マージ → Actions が plan → レビュアーが "snowflake-apply" を承認 → apply 実行
```
復旧: apply が途中で失敗したら、新しい PR で前に進めて直します。ノート PC からステートを手で編集してはいけません。

## このステップのコスト
検証は Snowflake クレジット 0。plan と apply はメタデータ操作のみ(数秒のクラウドサービス、ウェアハウスは使用しません)。公開リポジトリでは GitHub Actions の実行時間は無料です。

## 確認

```bash
gh pr checks                                  # 自分の PR で ci と terraform の plan ジョブが成功している
gh run list --workflow terraform --limit 3    # マージ後: apply の実行が承認を待ち、その後完了する
```
`.tf` ファイルを変更する PR を開くと、`ci` が成功し、`terraform` ワークフローに plan が表示されること。マージ後、`apply` ジョブが承認を待ち、承認後に `Apply complete` と報告されること。ローカルで `source scripts/tf-env` のあと `terraform -chdir=terraform/envs/handson plan` を実行し、`No changes` になることでも確認できます。

---
<!-- nav:bottom -->
[🏠 7日間の流れ](../../../README.ja.md#7日間の流れ) · ← [07 監視と FinOps](07-monitoring-finops-teardown.md) · [付録 AWS](appendix-aws.md) →
<!-- /nav:bottom -->
