# 04 · ガバナンス: 列・行・ロールによる制御

<!-- nav:top -->
[🏠 7日間の流れ](../../../README.ja.md#7日間の流れ) · ← [05 変換と Iceberg](05-transform-and-iceberg.md) · [06 BI と AI](06-bi-and-ai.md) →
<!-- /nav:top -->

**English:** [../../guides/04-governance.md](../../guides/04-governance.md)

**前提:** CURATED テーブルが存在すること(ガイド 05 の §1、Dynamic Tables)。ペルソナは設計上 RAW にアクセスできません。

## 作るもの
| 制御 | オブジェクト | 効果 |
|---|---|---|
| タグ | `HANBIT_GOV.TAGS.SENSITIVITY` = PII / HEALTH / CREDIT / FINANCIAL | 列を分類 |
| マスキング(列) | `MASK_SENSITIVE_STRING`、`MASK_SENSITIVE_NUMBER` を**タグに**紐づけ | タグ付きの列は、今も将来も保護される |
| 行アクセス | `RAP_REGION` + テーブル `ENTITLEMENTS.ROLE_REGION` | どのロールがどの地域を見られるかは**データ** |
| プロジェクション | `MARKETING.CUSTOMER_ID` の `PROJ_ID_JOINABLE` | 結合・絞り込みはでき、マーケティングは SELECT できない |
| 集約 | `MARKETING` の `AGG_MIN_GROUP_5` | マーケティングは 5 件以上のグループしか見られない |

## 手順
ガイド 02 の apply で、ポリシー、タグ、`RAP_REGION`、`ROLE_REGION` はすでに作成済みです。残るのはそれらをデータに適用する作業で、CURATED テーブル(ガイド 05 の第 1 節、`scripts/apply-curated --execute`)が必要です。リポジトリのルートで、`PRIVATE_KEY_PASSPHRASE` を export し、`source scripts/tf-env` を有効にして実行します。

```bash
# 1. CURATED テーブルがあること(Dynamic Table が 6 つ)
snow sql -c handson_tf -q "SHOW DYNAMIC TABLES IN DATABASE HANBIT_CURATED"

# 2. CURATED の列タグ(RAW には付けない)
scripts/gen-data --execute --emit-tag-map terraform/envs/handson/tags.auto.tfvars.json  # git 管理外。Terraform は *.auto.tfvars.json を自動で読み込む
grep -c . terraform/envs/handson/tags.auto.tfvars.json                      # 期待: 13 行(4 ドメインの 11 列)
echo 'apply_column_tags = true' >> terraform/envs/handson/terraform.tfvars   # git 管理外。以後の plan/apply でもタグを維持する
terraform -chdir=terraform/envs/handson plan                                 # 期待: snowflake_tag_association が 11 件追加
terraform -chdir=terraform/envs/handson apply

# 3. 行アクセス、集約ポリシー、サービスユーザーの認証ポリシー
scripts/apply-policies --execute                                             # 再実行しても安全
```
続いてアクセスマトリクス(下記)で検証します。

- `-var` で一度だけ渡すのではなく、`terraform.tfvars` に `apply_column_tags = true` を書いてください。一度きりの `-var` だと、次の通常の `plan` / `apply`(自分でもCIでも)がタグを不要と判断して外してしまいます。`tags.auto.tfvars.json` も git 管理外なので、CI では `TFVARS_JSON` に入れる必要があります(ガイド 08)。
- **`terraform plan` に差分がなくても、このガイドが完了したとは限りません。** フラグがないと、Terraform は列タグをまったく計画しません。
- `apply-policies` が「already has a AUTHENTICATION_POLICY」で失敗した場合: 以前の失敗した Terraform apply がすでに `AP_SERVICE` を `TERRAFORM` ユーザーに適用していました(プロバイダーが読み戻せず、エラーとして報告していました)。スクリプトは `SET ... FORCE` を使うようになったので、再実行しても安全です。

## 設計の理由
- **タグベースのマスキング**はスケールします。新しいタグ付き列には DDL を追加せずに保護が効きます。マスキングポリシーはデータ型ごと・タグごとに 1 つしか付けられないため、ポリシー内でタグの値によって分岐します。
- **権限テーブル**により、アクセス規則の変更がコードレビューのサイクルに縛られず、監査は `SELECT` で行えます。
- **`IS_ROLE_IN_SESSION`** はロール階層を考慮します。`CURRENT_ROLE()` は権限テーブルの参照にだけ使います。
- クラウドとの対応: マスキング ≈ BigQuery のポリシータグ / Lake Formation の列フィルタ、行アクセス ≈ Lake Formation のデータセルフィルタ / BigQuery の行アクセスポリシー。
- **Business Critical 限定(構築しない):** Tri-Secret Secure(顧客管理キー)、PrivateLink、フェイルオーバー。

## このステップのコスト
分類とポリシーテストを含めて約 6 クレジット。

## 確認

```bash
snow sql -c handson_tf -q "SHOW MASKING POLICIES IN SCHEMA HANBIT_GOV.POLICIES"      # MASK_SENSITIVE_STRING、MASK_SENSITIVE_NUMBER
snow sql -c handson_tf -q "SHOW ROW ACCESS POLICIES IN SCHEMA HANBIT_GOV.POLICIES"   # RAP_REGION
snow sql -c handson_tf -q "SELECT * FROM TABLE(HANBIT_CURATED.INFORMATION_SCHEMA.TAG_REFERENCES_ALL_COLUMNS('HANBIT_CURATED.CLAIMS.CLAIMS','table'))"   # タグ付きの列(例: DIAGNOSIS_CODE)
scripts/access-matrix                                                               # コアのケースがすべて成功する
scripts/verify-step 04 --execute
```
2 つのマスキングポリシーと `RAP_REGION` が一覧に表示され、3 つ目の結果にタグ付きの列が出ること(空なら列タグはまだ未適用です)、マトリクスに `FAIL` の行が出ないこと。前提: ガイド 05 の第 1 節が完了していて(CURATED テーブルがある)、上の `terraform` コマンドでは `source scripts/tf-env` が有効であること。Snowsight でペルソナとして確認するには、`USE ROLE CLAIMS_ADJUSTER;` のあと `SELECT * FROM HANBIT_CURATED.CLAIMS.CLAIMS LIMIT 5;` を実行します(ガイド 02 の `grant_personas_to_user` が必要です。ソウルの行だけが見え、このロールは診断を読めますが、他のペルソナにはマスクされます。これはアクセスマトリクスが確認します)。

## 検証: アクセスマトリクス
テストできないガバナンスは、制御ではなく主張にすぎません。`sql/matrix/access-matrix.yaml` に、ペルソナ × オブジェクト × 期待結果(`visible`、`masked`、`hashed`、`denied`、`rows`、`regions`)を列挙しています。ランナーは `USE ROLE` でロールを切り替えてクエリを実行し、結果を比較します。
```bash
scripts/access-matrix --dry-run     # 構文チェックのみ
scripts/access-matrix               # コアのケース(6 ペルソナ)。--stretch でドメイン横断のケースも実行
```
- `denied` が成功と判定されるのは、権限エラーまたはポリシーエラーの場合だけです。ネットワークやウェアハウスのエラーは実行を中断します(そうでないと「成功」に見えてしまうため)。
- **わざと壊す:** `ALTER TAG HANBIT_GOV.TAGS.SENSITIVITY UNSET MASKING POLICY HANBIT_GOV.POLICIES.MASK_SENSITIVE_STRING;` を実行して再実行すると、`masked` のケースが「leak」で失敗します。`terraform apply` で元に戻します。
- その後、マトリクス自身の読み取りを監査します: `sql/audit.sql`(ガイド 07)。

---
<!-- nav:bottom -->
[🏠 7日間の流れ](../../../README.ja.md#7日間の流れ) · ← [05 変換と Iceberg](05-transform-and-iceberg.md) · [06 BI と AI](06-bi-and-ai.md) →
<!-- /nav:bottom -->
