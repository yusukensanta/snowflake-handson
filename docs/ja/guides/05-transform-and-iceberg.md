# 05 · 変換と Iceberg

**English:** [../../guides/05-transform-and-iceberg.md](../../guides/05-transform-and-iceberg.md)

## 1. Dynamic Tables による変換(ガイド 04 より先に行います)
**Dynamic Table** は、`TARGET_LAG` の範囲内で Snowflake が最新状態に保つ宣言的なクエリです。結果を記述すると、Snowflake が増分更新をスケジュールします。クラウドでの類似: 鮮度 SLA 付きのマテリアライズドビュー、または dbt モデルとそのスケジューラを 1 つにまとめたもの。

```bash
scripts/gen-data --emit-curated sql/curated.sql   # コミット済み。単一のスキーマ定義から再生成可能
scripts/apply-curated --dry-run
scripts/apply-curated                              # HANBIT_CURATED に Dynamic Table 6 つとデータメトリックファンクション
```
CURATED 層で行うこと: ビジネスキーで重複排除し、列名を維持して(タグベースのマスキングがそのまま効くように)、`CUSTOMER_PSEUDO_ID = SHA2(customer_id || ソルト)` を追加します。これにより、不正対策やマーケティングは生の識別子なしで結合できます。

**`IF NOT EXISTS` を使う理由:** `CREATE OR REPLACE` は、テーブルに付けたマスキング/行ポリシーを黙って削除してしまいます。定義を変えるときは、そのテーブルを意図的に削除して作り直し、`scripts/apply-policies` を再実行してください。

**ラグとコスト:** `TARGET_LAG = '1 hour'` なら更新は少なく済みます。ラグ 1 分では `TRANSFORM_WH` が起き続け、コストが何倍にもなります。計測するには、1 日後に `TRANSFORM_WH` の `V_CREDITS_BY_WAREHOUSE` を比較します。使わないときはサスペンドします:
```bash
scripts/cost-guard --suspend-all     # ウェアハウスと Dynamic Table をサスペンド
```
**データ品質:** `sql/dmf.sql` が、各キー列に `NULL_COUNT` と `DUPLICATE_COUNT` のデータメトリックファンクションを(毎時)付与します。結果は `SNOWFLAKE.LOCAL.DATA_QUALITY_MONITORING_RESULTS` に出ます。

## このステップ(変換)のコスト
約 8 クレジット。ほとんどは XS での 120 万行の初回フルリフレッシュです。

## 確認(変換)
`SELECT COUNT(*) FROM HANBIT_CURATED.CLAIMS.CLAIMS` が RAW の件数と一致し、`SHOW DYNAMIC TABLES IN DATABASE HANBIT_CURATED` で `scheduling_state = ACTIVE` になっていること。

## 2. Snowflake 管理ストレージ上の Iceberg v3
Apache Iceberg はオープンなテーブルフォーマットです。データは Parquet ファイルとメタデータで構成され、どのエンジンからも読めます。**Snowflake をカタログ、Snowflake 管理ストレージを保存先**にすると、S3 バケットや IAM ロールを自分で用意せずにオープン形式のテーブルを使えます(AWS バケット版は付録にあり、リポジトリのオーナーは適用しません)。クラウドでの類似: Glue/Hive 方式の Iceberg テーブルから、ストレージ周りの配線を除いたもの。

```bash
snow sql -c handson_tf -f sql/iceberg.sql      # HANBIT_MARTS.LAKE.CLAIMS_FACT を作成(ICEBERG_VERSION = 3)
```
- `ICEBERG_VERSION` は作成時に固定されます(`ALTER` では変更できません)。既定は v2 で、このラボでは v3 を明示します。確認は `SHOW PARAMETERS LIKE 'ICEBERG_VERSION' IN TABLE ...` で行います。
- テーブルには仮名化済みで機微でない列だけを入れます。**外部エンジンは、Horizon カタログ経由で接続しない限り、マスキングポリシーや行アクセスポリシーの対象外**です。そのため、生の PII をオープン形式のテーブルに公開してはいけません。これがこの節のガバナンス上の最大の教訓です。

### Snowflake の外から読む
最小権限のユーザー/ロール用にプログラマティックアクセストークンを作成し、環境変数に設定します(コミットしないこと)。その後:
```bash
export SNOWFLAKE_ACCOUNT_URL="https://<your-account>.snowflakecomputing.com"
export SNOWFLAKE_PAT="<token>"
scripts/open-read          # Horizon Iceberg REST カタログ経由で PyIceberg が読み取り
```

### フォールバック
ap-northeast-2 のトライアルでは、Snowflake 管理の Iceberg ストレージや v3 が有効でない場合があります。`scripts/preflight` が確認します。`sql/iceberg.sql` が失敗したら、この節は概念の学習にとどめ、エラーをメモして先へ進んでください。後続のガイドはこれに依存しません。

## このステップ(Iceberg)のコスト
約 1 クレジット(XS での CTAS 1 回とストレージ)。

## 確認(Iceberg)
`SELECT COUNT(*) FROM HANBIT_MARTS.LAKE.CLAIMS_FACT` が CURATED の claims 件数と一致し、`ICEBERG_VERSION` パラメータが `3` であること。
