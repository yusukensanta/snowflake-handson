# 02 · RBAC と Terraform

**English:** [../../guides/02-rbac-and-terraform.md](../../guides/02-rbac-and-terraform.md)

## 1. サービス ID として Terraform を実行
```bash
export PRIVATE_KEY_PASSPHRASE='...'          # シェルで入力し、ファイルには書かない
terraform -chdir=terraform/envs/handson init
terraform -chdir=terraform/envs/handson plan  # ウェアハウス(XS、auto-suspend 60 秒)、ペルソナロール 9 個、モニター 4 個
terraform -chdir=terraform/envs/handson apply
terraform -chdir=terraform/envs/handson plan  # "No changes" になること
```
プロバイダは `versions.tf` で固定しています(`2.23.0`)。リソース名は推測ではなくプロバイダのスキーマから確認しました。集約ポリシー、予算、データメトリックファンクションの付与にはリソースがないため、`sql/` から適用します。

## 2. RBAC のパターン
- **オブジェクトの所有**は Terraform のロールが持ち、人間はオブジェクトを所有しません。
- **アクセスロール**(`<DOMAIN>_RO`, `<DOMAIN>_RW`)がスキーマの権限を持ち、**機能ロール**(ペルソナ)にアクセスロールを付与します。ユーザーには機能ロールだけを付与します。
- マネージドアクセススキーマを使い、権限を付与できるのはスキーマ所有ロールだけにします。
- クラウドとの対応: アクセスロール ≈ IAM ポリシー、機能ロール ≈ IAM ロール/グループ、`TF_ADMIN` ≈ CI のデプロイ用ロール。

## このステップのコスト
検証クエリで約 1 クレジット。

## 確認
2 回目の `terraform plan` が `No changes` と表示すること。

## 3. import ラボ: 手作業で作ったオブジェクトを取り込む
実際のチームは画面操作から始まります。Terraform は、既存のオブジェクトを作り直さずに管理下へ取り込めます。

1. Snowsight(ロール `TF_ADMIN`)で次を手作業で作成します:
   `CREATE ROLE LAB_IMPORT_ROLE;` と `CREATE WAREHOUSE LAB_IMPORT_WH WAREHOUSE_SIZE = XSMALL AUTO_SUSPEND = 60;`
2. `terraform/envs/handson/import-lab/lab.tf.example` を `terraform/envs/handson/lab.tf` にコピーします。
3. `terraform plan` が 2 件の import を表示します。変更も表示される場合は、設定が実態と違います。オブジェクトではなく設定を直してください。
4. `terraform apply` のあと、もう一度 `terraform plan` を実行すると `No changes` になります。
5. **ドリフト:** Snowsight で `ALTER WAREHOUSE LAB_IMPORT_WH SET WAREHOUSE_SIZE = SMALL;` を実行し、`terraform plan` を実行すると差分が表示され、元に戻そうとします。管理外の変更はこうして検出できます。
6. 後片付け: `lab.tf` を消す前に `terraform destroy -target=snowflake_account_role.lab -target=snowflake_warehouse.lab` を実行します(または Snowsight で両方を削除し、`terraform state rm` します)。

既存オブジェクトの属性を調べたいときは、`import` ブロックだけを書いて `terraform plan -generate-config-out=generated.tf` を実行し、内容を確認してから採用します。

## import ラボのコスト
0.1 クレジット未満(クエリを実行しない XS ウェアハウス)。

## 確認(import ラボ)
手順 4 の後に `No changes. Your infrastructure matches the configuration.` と表示されること。

## 4. データベース、アクセスロール、ペルソナ、タグ
`apply` 後、Terraform は次を作成します: `HANBIT_RAW/CURATED/MARTS/GOV`、36 個のアクセスロール(`RAW_CLAIMS_RO`、`CURATED_LENDING_RW` など)、アクセスロールとウェアハウス `USAGE` を付与された 9 個のペルソナロール、`HANBIT_GOV.TAGS` の `SENSITIVITY` タグ。

列タグは、CURATED テーブルが存在してからガイド 04 で適用します(それ以前に適用すると、存在しない列でエラーになります)。
ペルソナをテストするには、git 管理対象外の `terraform.tfvars` に `grant_personas_to_user = "<あなたのユーザー名>"` を入れます。Snowsight で `USE ROLE CLAIMS_ADJUSTER` などが使えるようになります。

ここでのルール: ペルソナロール以外をユーザーに直接付与しない。`DATA_PLATFORM_ENGINEER` は RAW/CURATED への RW を持つが(ガイド 04 の後は)PII がマスクされる。`AUDITOR` と `SECURITY_ADMIN_FN` はデータ用ロールを一切持たない。

クラウドとの対応: タグ + マスキングポリシー ≈ Lake Formation の LF-Tag や BigQuery のポリシータグによる列レベルセキュリティ。
