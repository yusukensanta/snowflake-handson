# 03 · データ取り込み

<!-- nav:top -->
[🏠 7日間の流れ](../../../README.ja.md#7日間の流れ) · ← [02 RBAC と Terraform](02-rbac-and-terraform.md) · [05 変換と Iceberg](05-transform-and-iceberg.md) →
<!-- /nav:top -->

**English:** [../../guides/03-ingestion.md](../../guides/03-ingestion.md)

AWS アカウントは不要です。ファイルは Snowflake の**内部ステージ**(Snowflake が暗号化)に置き、行は **Snowpipe Streaming** で直接送ることもできます。

| 経路 | 使う場面 | クラウドでの類似 |
|---|---|---|
| `PUT` + `COPY INTO`(バッチ) | すでにあるファイル | `aws s3 cp` + Redshift の `COPY`、BigQuery のロードジョブ |
| Snowpipe Streaming(行単位) | イベント/行を送るプロデューサー、低遅延 | Kinesis Firehose / BigQuery Storage Write API |
| (付録)S3 + Snowpipe 自動取り込み | AWS アカウントがある場合 | S3 イベント → SQS → ローダー |

## 1. 合成データの生成
```bash
scripts/gen-data                 # 6 ドメイン × 20 万行 → data/out/*.csv.gz(圧縮後 約 21 MB、非圧縮 約 85 MB)
scripts/gen-data --rows 1000     # 学習中は小さく実行
```
同じシードなら同一のバイト列になります。国民 ID 風の番号は、チェックディジットを意図的に不正にしています。

## 2. スキーマ、ステージ、ファイル形式の作成(Terraform)
`terraform -chdir=terraform/envs/handson apply` で `HANBIT_RAW/CURATED/MARTS`、ドメインごとのマネージドアクセススキーマ、RAW の各スキーマに `LANDING` 内部ステージと `CSV_GZ` ファイル形式が作られます。

## 3. バッチロード
```bash
scripts/load-batch --dry-run
scripts/load-batch               # ガイド 02 のロール付与が済むまでは TERRAFORM のアイデンティティで実行
scripts/load-batch               # もう一度: 新規ロードは 0 行(COPY はロード済みファイルを記憶)
```
`sql/raw_tables.sql` は単一のスキーマ定義から生成されます(`scripts/gen-data --emit-ddl sql/raw_tables.sql`)。差異が出るとテストが失敗します。

## 4. ストリーミングロード
```bash
scripts/stream-load --domain claims --file data/out/claims.csv.gz
```
行は高性能 SDK(鍵ペア認証、バッチごとのオフセットトークン)を通じて `HANBIT_RAW.CLAIMS.CLAIMS_STREAM` に入ります。`PRIVATE_KEY_PASSPHRASE` の export が必要です。`src/sfops/streaming.py` の `sdk_properties` が、`handson_tf` プロファイルを SDK のキー(`url`、`user`、`private_key_file`、`private_key_passphrase`、`role`)に変換します。**実アカウントでの完了は未確認です**。失敗した場合はエラーを貼ってください。

## このステップのコスト
約 8 クレジット(XS の `LOAD_WH`、auto-suspend 60 秒)。ストリーミングはウェアハウス時間ではなく取り込み量に課金されます。

## 確認

```bash
snow sql -c handson_tf --warehouse LOAD_WH -q "SELECT COUNT(*) AS n FROM HANBIT_RAW.CLAIMS.CLAIMS"
snow sql -c handson_tf --warehouse LOAD_WH -q "SELECT COUNT(*) AS n FROM HANBIT_RAW.CLAIMS.CLAIMS_STREAM"   # ストリーミングの手順の後
snow sql -c handson_tf -q "LIST @HANBIT_RAW.CLAIMS.LANDING"                                                # ステージされた claims.csv.gz
scripts/verify-step 03
```
期待する結果:
- 1 つ目の件数が `--rows`(既定 20 万)と一致すること。ほかの 5 ドメイン(`LENDING`、`FINANCE`、`UNDERWRITING`、`RISK_FRAUD`、`MARKETING`)も、スキーマとテーブル名を変えて同様に確認します。
- 2 回目の `scripts/load-batch` では、各 `COPY` が `0 files processed` で終わり、件数が変わらないこと。
- `_STREAM` の件数が、ストリーミングしたファイルの行数と一致すること。
- `scripts/verify-step 03` は CLAIMS テーブルに行があることしか確認しないので、件数は自分の目で確認してください。

---
<!-- nav:bottom -->
[🏠 7日間の流れ](../../../README.ja.md#7日間の流れ) · ← [02 RBAC と Terraform](02-rbac-and-terraform.md) · [05 変換と Iceberg](05-transform-and-iceberg.md) →
<!-- /nav:bottom -->
