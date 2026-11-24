# 08 · CI と GitHub Actions からの apply

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
5. **ネットワークポリシー:** GitHub ホストランナーの IP は変動します。`TERRAFORM` ユーザーには `NP_HANDSON` を強制しないでください。CI がサインインできなくなります。人間のユーザーは引き続き制限します。

## スクリプトによるセットアップ(手順 3 と 4)
`scripts/setup-github` は、GitHub CLI を使って、必須レビュアー付きの 2 つの環境の作成、`snowflake-apply` の `main` への限定、変数とシークレットの登録、必要なら `main` のブランチ保護までを行います。冪等なので、シークレットのローテーションにも再実行できます。リポジトリ管理者として `gh auth login` が必要です。
```bash
export TF_CLOUD_ORGANIZATION=… TF_WORKSPACE=… TF_API_TOKEN=…
export PLAN_SNOWFLAKE_USER=TERRAFORM_PLAN  PLAN_SNOWFLAKE_ROLE=TF_PLAN   PLAN_SNOWFLAKE_PRIVATE_KEY_FILE=~/.snowflake/plan.p8
export APPLY_SNOWFLAKE_USER=TERRAFORM      APPLY_SNOWFLAKE_ROLE=TF_ADMIN APPLY_SNOWFLAKE_PRIVATE_KEY_FILE=~/.snowflake/ci.p8
export SNOWFLAKE_ORGANIZATION_NAME=… SNOWFLAKE_ACCOUNT_NAME=…           # 両環境で共通
scripts/setup-github --dry-run --branch-protection   # プレビュー(呼び出しのみ表示し、値は表示しません)
scripts/setup-github --branch-protection
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
`.tf` ファイルを変更する PR を開くと、`ci` が成功し、`terraform` ワークフローに plan が表示されること。マージ後、`apply` ジョブが承認を待ち、承認後に `Apply complete` と報告されること。
