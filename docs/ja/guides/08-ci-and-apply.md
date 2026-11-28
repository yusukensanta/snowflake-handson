# 08 · CI と GitHub Actions からの apply

<!-- nav:top -->
[🏠 7日間の流れ](../../../README.ja.md#7日間の流れ) · ← [07 監視と FinOps](07-monitoring-finops-teardown.md) · [付録 AWS](appendix-aws.md) →
<!-- /nav:top -->

**English:** [../../guides/08-ci-and-apply.md](../../guides/08-ci-and-apply.md)

業務上のルール: **plan はどこでも、apply は人間が承認した後に CI からのみ。** 最初の apply(ガイド 02)はアカウントのブートストラップのためローカルから行い、CI を設定した後はこのフローに切り替えます。

## ワークフロー
| ファイル | 実行タイミング | 内容 |
|---|---|---|
| `.github/workflows/ci.yml` | すべての PR と `main` への push | `ruff`、`ty`、`pytest`(カバレッジ 80% 以上)、`shellcheck`、`scripts/check-secrets`、`terraform fmt` + `validate`(認証情報は不要) |
| `.github/workflows/terraform.yml` | `terraform/**` を変更する PR と push | PR: `plan`(ジョブのサマリーに表示)。`main`: `plan` の後、`snowflake-apply` 環境の承認を経て **`apply`** |

アクションはコミット SHA で固定し、権限は `contents: read` のみです。plan ファイルはアーティファクトとしてアップロードしません(公開リポジトリのアーティファクトは誰でも取得でき、plan にはシークレットが含まれうるため)。フォークからの PR にシークレットは渡されません。

## 初回セットアップ
1. **共有ステート。** ローカルの plan と CI の apply は同じステートを使う必要があります。無料の HCP Terraform で組織とワークスペースを作り、*Execution mode* を **Local**(ステート保管のみ)にします。その後ローカルで: `cp terraform/envs/handson/backend.tf.example terraform/envs/handson/backend.tf`(git 管理対象外)、`export TF_CLOUD_ORGANIZATION=… TF_WORKSPACE=…`、`terraform login`、`terraform init -migrate-state`。
2. **CI 用の ID。** `TERRAFORM` ユーザーに CI 専用の 2 つ目の公開鍵を登録します(`ALTER USER TERRAFORM SET RSA_PUBLIC_KEY_2='…'`)。ノート PC の鍵とは独立してローテーションできます。
3. **GitHub Environments**(Settings > Environments): `snowflake-plan`(**必須レビュアー**を設定。ワークフローの変更を含む PR のコードは、あなたが内容を確認した後でのみ認証情報付きで実行されます)と `snowflake-apply`(**必須レビュアー**、デプロイ対象ブランチは `main` のみ)。シークレットは環境にだけ登録し、各ジョブは自分の環境のものだけを読みます。**`snowflake-plan` には別の読み取り専用の Snowflake ID**(別ユーザーと、リフレッシュに必要な範囲に絞ったロール)を使い、`TF_ADMIN` の鍵は `snowflake-apply` にだけ置きます。変数 `SNOWFLAKE_ROLE` は環境ごとに設定します。シークレット:
   `SNOWFLAKE_ORGANIZATION_NAME`、`SNOWFLAKE_ACCOUNT_NAME`、`SNOWFLAKE_USER`、`SNOWFLAKE_PRIVATE_KEY`、`SNOWFLAKE_PRIVATE_KEY_PASSPHRASE`、`TF_API_TOKEN`、必要なら `TFVARS_JSON`(非公開の tfvars の内容を JSON にしたもの)。変数: `TF_CLOUD_ORGANIZATION`、`TF_WORKSPACE`。
4. **`main` のブランチ保護:** `ci` のチェックとプルリクエストを必須にします。
5. **ネットワークポリシー:** GitHub ホストランナーの IP は変動します。`enforce_account_policies = false` のままにしてください([ガイド 07](07-monitoring-finops-teardown.md) のセクション 2)。このフラグは `NP_HANDSON` をアカウント全体に適用するため、`TERRAFORM` と plan 用ユーザーもブロックされ、CI がサインインできなくなります。

## シークレットと変数の一覧
ワークフローが読み取るすべての値です。ここにある値は一切コミットしません。`scripts/setup-github`(後述)がすべて設定します。

| 名前 | 種類 | スコープ | 内容と入手方法 |
|---|---|---|---|
| `TF_CLOUD_ORGANIZATION` | 変数 | リポジトリ | HCP Terraform の組織名(app.terraform.io > Organizations) |
| `TF_WORKSPACE` | 変数 | リポジトリ | ステートを保管するワークスペース(*Execution mode = Local*) |
| `TF_API_TOKEN` | シークレット | 各環境 | HCP Terraform の API トークン。個人ユーザートークンではなく、そのワークスペースに限定した**チームトークン**(Settings > Teams)を作成します |
| `SNOWFLAKE_ORGANIZATION_NAME` | シークレット | 各環境 | `SELECT CURRENT_ORGANIZATION_NAME();` |
| `SNOWFLAKE_ACCOUNT_NAME` | シークレット | 各環境 | `SELECT CURRENT_ACCOUNT_NAME();`(URL 全体ではなく名前のみ) |
| `SNOWFLAKE_USER` | シークレット | 各環境 | apply は `TERRAFORM`。plan は別の読み取り専用ユーザー |
| `SNOWFLAKE_PRIVATE_KEY` | シークレット | 各環境 | そのユーザーの PEM 秘密鍵(下で生成)。改行は保持されます |
| `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE` | シークレット | 各環境 | 鍵のパスフレーズ。暗号化していない鍵なら省略(非推奨) |
| `SNOWFLAKE_ROLE` | 変数 | 各環境 | apply は `TF_ADMIN`。plan は読み取り専用ロール |
| `TFVARS_JSON` | シークレット | 各環境 | 任意。非公開の `terraform.tfvars` を JSON にしたもの(例: `allowed_ips`、`alert_email`、`grant_personas_to_user`) |

アカウント情報を変数ではなくシークレットにしているのは意図的です。このリポジトリは公開されており、シークレットの値はログ上でマスクされます。

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
