# 06 · BI と AI

<!-- nav:top -->
[🏠 7日間の流れ](../../../README.ja.md#7日間の流れ) · ← [04 ガバナンス](04-governance.md) · [07 監視と FinOps](07-monitoring-finops-teardown.md) →
<!-- /nav:top -->

**English:** [../../guides/06-bi-and-ai.md](../../guides/06-bi-and-ai.md)

## 1. BI: Snowflake 内の Streamlit ダッシュボード
`apps/streamlit/` は、地域別の保険金請求を表示する小さなダッシュボードです。Snowflake の中で動くため、データはアカウントの外に出ません。Streamlit アプリは**所有者権限(owner's rights)**で実行されます。クエリには閲覧者ではなく、アプリを所有するロールの権限とポリシーが使われます。つまり所有者をどのロールにするかがセキュリティ上の判断になります。そのため、アプリは管理者ロールではなく、このデータを必要とするペルソナ(`CLAIMS_ADJUSTER`)に所有させます。

**前提:** ガイド 04 が完了し、`grant_personas_to_user` に `handson_admin` 接続のユーザーを設定して適用済みであること(ガイド 02)。`PRIVATE_KEY_PASSPHRASE` をエクスポートした状態で、リポジトリのルートから実行します。

```bash
snow sql -c handson_tf -f sql/streamlit.sql          # 1. TF_ADMIN: スキーマ、ステージ、権限
snow sql -c handson_admin -f sql/streamlit_app.sql   # 2. CLAIMS_ADJUSTER: ファイルをアップロードし、アプリを作成
```
- 接続を 2 つに分けるのは、請求データを読めるロールが必要なのは手順 2 だけで、Terraform のサービスユーザーにはそのロールを与えないためです。
- 手順 2 は、アプリの作成時にファイルをアプリへコピーします。アプリを編集したら再実行してください(アプリに付与した `USAGE` 権限は失われます)。

Snowsight の **Projects > Streamlit > CLAIMS_DASH** を `CLAIMS_ADJUSTER` で開くと、Seoul の行だけが表示されます。他のペルソナはアプリを開けません。アクセスを許可しても、各自のビューではなく同じ Seoul の行が見えます。ステータスの絞り込みは `queries.py` でホワイトリスト化されており(ユニットテスト済み)、ユーザー入力を文字列連結することはありません。保険金請求の担当者にコスト情報は不要なので、プラットフォームのクレジットはこのダッシュボードに載せていません。`scripts/cost-report` を使います(ガイド 07)。

## 2. AI: Cortex Analyst(Seoul ではスキップ)
2026-11-27 時点で、[Cortex Analyst のドキュメント](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst)のネイティブ対応リージョンに AWS ap-northeast-2(Seoul)はなく、このリージョンではリージョン間推論が必要です。**このリポジトリの方針: リージョン内に留める。** アカウントが Seoul の場合、この節はスキップします。`scripts/preflight` は `CORTEX_ENABLED_CROSS_REGION` を表示しますが、利用可否は確認せず、設定も変更しません。

利用するリージョンが一覧にある場合(以下の手順は実アカウントでは未実行です):
1. **先にコスト管理の方法を確認する。** Analyst はメッセージ数で課金され、生成された SQL の実行にはウェアハウスの料金もかかります。利用状況は `CORTEX_ANALYST_USAGE_HISTORY` ビューで確認し、終わったら `ALTER ACCOUNT SET ENABLE_CORTEX_ANALYST = FALSE;`(ACCOUNTADMIN)で無効化できます。`CORTEX_CODE_CLI_DAILY_EST_CREDIT_LIMIT_PER_USER` が上限をかけるのは Cortex Code CLI だけで、Analyst には効きません。
2. セマンティックビュー `sql/semantic_view.sql` を作成します。機微でない列だけを公開します。このファイルは権限を付与しません。質問するロールには、データベースロール `SNOWFLAKE.CORTEX_USER` または `SNOWFLAKE.CORTEX_ANALYST_USER` と、ビューの元テーブルへの `SELECT` が必要です。
3. Cortex Analyst に「地域別の直近四半期の請求額合計」と質問し、生成された SQL をダッシュボードのクエリと比較します。
4. **ガバナンス確認:** 診断コードを尋ねます。セマンティックビューはその列を含まないため、回答の材料がありません。`MARKETING_ANALYST` はそもそも請求テーブルへの `SELECT` がありません。これで分かるのはビューの公開範囲と権限の効果で、マスキングではありません。マスキングを証明するのはアクセスマトリクス(ガイド 04)です。

## このステップのコスト
ダッシュボード: 約 2 クレジット(BI_WH、自動サスペンド 60 秒)。AI: スキップすれば 0。実行する場合は数回の質問分で、メッセージ数による課金です。

## 確認

```bash
snow sql -c handson_admin --role CLAIMS_ADJUSTER -q "SHOW STREAMLITS IN SCHEMA HANBIT_MARTS.APPS"   # CLAIMS_DASH
snow sql -c handson_tf -q "LIST @HANBIT_MARTS.APPS.STREAMLIT_STAGE/claims"                          # app.py、queries.py、environment.yml
scripts/verify-step 06 --execute
```
`verify-step` はクエリが実行できることしか確認しないため、1 つ目の出力に `CLAIMS_DASH` があることは自分で確認してください。そのあと上記の手順でアプリを開き、Seoul の行だけが表示されることを確認します。

---
<!-- nav:bottom -->
[🏠 7日間の流れ](../../../README.ja.md#7日間の流れ) · ← [04 ガバナンス](04-governance.md) · [07 監視と FinOps](07-monitoring-finops-teardown.md) →
<!-- /nav:bottom -->
