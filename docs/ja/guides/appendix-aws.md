# 付録 · Iceberg 用の自分の S3 バケット(任意)

<!-- nav:top -->
[🏠 7日間の流れ](../../../README.ja.md#7日間の流れ) · ← [08 CI と apply](08-ci-and-apply.md)
<!-- /nav:top -->

**English:** [../../guides/appendix-aws.md](../../guides/appendix-aws.md)

コースの本線では AWS アカウントは不要です(Snowflake 管理ストレージを使います)。この付録は、AWS アカウントを持っていて、Iceberg のデータを**自分のバケット**に置きたい場合にだけ使ってください。リポジトリのオーナーは適用しておらず、`terraform validate` による検証のみのため、調整が必要になる可能性があります。

1. `terraform/modules/aws_appendix/main.tf` を確認します: プライベートバケット(パブリックアクセスをブロック、KMS 暗号化)、**外部 ID** 付きで Snowflake を信頼する IAM ロール(confused deputy 問題を防ぎます)、最小権限の S3 アクセス。
2. 信頼用の 2 つの変数を空のまま apply し、`DESC EXTERNAL VOLUME HANBIT_LAKE_VOL` から Snowflake の IAM ユーザー ARN と外部 ID を取得します。
3. `snowflake_iam_user_arn` と `snowflake_external_id` を(git 管理対象外の tfvars に)設定し、もう一度 apply します。
4. 既定のストレージではなく `EXTERNAL_VOLUME = 'HANBIT_LAKE_VOL'` を指定して Iceberg テーブルを作成します。

アカウント ID、実 ID を含むロール ARN、tfvars は絶対にコミットしないでください。

## このステップのコスト
Snowflake 側: ガイド 05 とほぼ同じ。AWS 側: S3 のストレージとリクエストで、このデータ量なら数セント。

## 確認
`DESC EXTERNAL VOLUME HANBIT_LAKE_VOL` が成功し、テストテーブルがバケットに Parquet ファイルを書き込むこと。

---
<!-- nav:bottom -->
[🏠 7日間の流れ](../../../README.ja.md#7日間の流れ) · ← [08 CI と apply](08-ci-and-apply.md)
<!-- /nav:bottom -->
