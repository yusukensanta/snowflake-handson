# 04 · ガバナンス: 列・行・ロールによる制御

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
```bash
terraform -chdir=terraform/envs/handson apply        # ポリシーとタグへの紐づけ
scripts/gen-data --emit-tag-map terraform/envs/handson/tags.auto.tfvars.json
terraform -chdir=terraform/envs/handson apply -var apply_column_tags=true   # CURATED の列タグ(RAW には付けない)
scripts/apply-policies                               # 権限テーブル、集約ポリシー、テーブルへの適用
```
続いてアクセスマトリクスで検証します(ガイド 04 の「検証」、コマンドは `scripts/access-matrix`)。

## 設計の理由
- **タグベースのマスキング**はスケールします。新しいタグ付き列には DDL を追加せずに保護が効きます。マスキングポリシーはデータ型ごと・タグごとに 1 つしか付けられないため、ポリシー内でタグの値によって分岐します。
- **権限テーブル**により、アクセス規則の変更がコードレビューのサイクルに縛られず、監査は `SELECT` で行えます。
- **`IS_ROLE_IN_SESSION`** はロール階層を考慮します。`CURRENT_ROLE()` は権限テーブルの参照にだけ使います。
- クラウドとの対応: マスキング ≈ BigQuery のポリシータグ / Lake Formation の列フィルタ、行アクセス ≈ Lake Formation のデータセルフィルタ / BigQuery の行アクセスポリシー。
- **Business Critical 限定(構築しない):** Tri-Secret Secure(顧客管理キー)、PrivateLink、フェイルオーバー。

## このステップのコスト
分類とポリシーテストを含めて約 6 クレジット。

## 確認
`scripts/access-matrix`(ガイド 04 の「検証」)でコアのケースがすべて成功すること。

## 検証: アクセスマトリクス
テストできないガバナンスは、制御ではなく主張にすぎません。`sql/matrix/access-matrix.yaml` に、ペルソナ × オブジェクト × 期待結果(`visible`、`masked`、`hashed`、`denied`、`rows`、`regions`)を列挙しています。ランナーは `USE ROLE` でロールを切り替えてクエリを実行し、結果を比較します。
```bash
scripts/access-matrix --dry-run     # 構文チェックのみ
scripts/access-matrix               # コアのケース(6 ペルソナ)。--stretch でドメイン横断のケースも実行
```
- `denied` が成功と判定されるのは、権限エラーまたはポリシーエラーの場合だけです。ネットワークやウェアハウスのエラーは実行を中断します(そうでないと「成功」に見えてしまうため)。
- **わざと壊す:** `ALTER TAG HANBIT_GOV.TAGS.SENSITIVITY UNSET MASKING POLICY HANBIT_GOV.POLICIES.MASK_SENSITIVE_STRING;` を実行して再実行すると、`masked` のケースが「leak」で失敗します。`terraform apply` で元に戻します。
- その後、マトリクス自身の読み取りを監査します: `sql/audit.sql`(ガイド 07)。
