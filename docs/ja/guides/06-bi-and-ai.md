# 06 · BI と AI

<!-- nav:top -->
[🏠 7日間の流れ](../../../README.ja.md#7日間の流れ) · ← [04 ガバナンス](04-governance.md) · [07 監視と FinOps](07-monitoring-finops-teardown.md) →
<!-- /nav:top -->

**English:** [../../guides/06-bi-and-ai.md](../../guides/06-bi-and-ai.md)

## 1. BI: Snowflake 内の Streamlit ダッシュボード
`apps/streamlit/` は小さなダッシュボードです(地域別の保険金請求と、プラットフォームのクレジット)。Snowflake の中で動くため、データはアカウントの外に出ず、ロールのマスキングポリシーと行アクセスポリシーもそのまま適用されます。管理者ロールではなく、最小権限のロールでデプロイしてください:
```bash
snow sql -c handson_tf -f sql/streamlit.sql   # ステージ、権限、アプリを作成
snow sql -c handson_tf -q "PUT file://apps/streamlit/* @HANBIT_MARTS.APPS.STREAMLIT_STAGE/claims AUTO_COMPRESS=FALSE OVERWRITE=TRUE"   # アプリのファイルをアップロード
```
Snowsight(Projects > Streamlit)を `CLAIMS_ADJUSTER` で開くと、Seoul の行だけが表示されます。ロールを切り替えると別のビューになります。ステータスの絞り込みは `queries.py` でホワイトリスト化されており(ユニットテスト済み)、ユーザー入力を文字列連結することはありません。

## 2. AI: Cortex / Cortex Code(Seoul で利用可能な場合のみ)
`scripts/preflight` が、ap-northeast-2 で Cortex が使えるか、リージョン間推論が必要かを報告します。**このリポジトリの方針: リージョン内に留める。** リージョン間推論が必要なら、この節はスキップします。

利用できる場合:
1. **先に利用上限を設定する**: `ALTER ACCOUNT SET CORTEX_CODE_CLI_DAILY_EST_CREDIT_LIMIT_PER_USER = <小さな値>;`(現在値は preflight が表示します)。AI 機能はトークン単位で課金され、想定外のコストになることがあります。
2. セマンティックビュー `sql/semantic_view.sql` を作成します。機微でない列だけを意図的に公開しているため、自然言語の質問が HEALTH データに届くことはありません。
3. Cortex Analyst に「地域別の直近四半期の請求額合計」と質問し、生成された SQL をダッシュボードのクエリと比較します。
4. **ガバナンス確認:** `MARKETING_ANALYST` で診断コードを尋ねます。回答は拒否またはマスクされるはずです。AI が Snowflake の統制を引き継ぐのは、データポリシーがアプリではなく列に付いているからです。

## このステップのコスト
ダッシュボード: 約 2 クレジット(BI_WH、自動サスペンド 60 秒)。AI: 上限設定の範囲で最大 5 クレジット。スキップすれば 0。

## 確認

```bash
snow sql -c handson_tf -q "SHOW STREAMLITS IN SCHEMA HANBIT_MARTS.APPS"          # CLAIMS_DASH
snow sql -c handson_tf -q "LIST @HANBIT_MARTS.APPS.STREAMLIT_STAGE/claims"       # app.py などアップロードしたファイル
scripts/verify-step 06 --execute
```
そのあと Snowsight の **Projects > Streamlit > CLAIMS_DASH** を開きます。`CLAIMS_ADJUSTER` では地域だけが表示されること。AI を有効にした場合は、機微な列への質問が拒否またはマスクされること。

---
<!-- nav:bottom -->
[🏠 7日間の流れ](../../../README.ja.md#7日間の流れ) · ← [04 ガバナンス](04-governance.md) · [07 監視と FinOps](07-monitoring-finops-teardown.md) →
<!-- /nav:bottom -->
