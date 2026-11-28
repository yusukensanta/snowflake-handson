# 07 · 監視、FinOps、後片付け

<!-- nav:top -->
[🏠 7日間の流れ](../../../README.ja.md#7日間の流れ) · ← [06 BI と AI](06-bi-and-ai.md) · [08 CI と apply](08-ci-and-apply.md) →
<!-- /nav:top -->

**English:** [../../guides/07-monitoring-finops-teardown.md](../../guides/07-monitoring-finops-teardown.md)

## 1. プラットフォームとパイプラインの監視
Terraform の `monitoring` モジュールが、`SNOWFLAKE.ACCOUNT_USAGE` 上に `HANBIT_OPS.MONITORING` のビューを作成します:

| ビュー | わかること |
|---|---|
| `V_COPY_ERRORS` | 失敗したバッチロードとその理由 |
| `V_PIPE_USAGE`, `V_TASK_RUNS` | ストリーミング/パイプとタスクの履歴 |
| `V_DYNAMIC_TABLE_REFRESHES` | CURATED テーブルの更新状態とラグ |
| `V_FAILED_LOGINS` | ログイン失敗と接続元 IP |
| `V_CREDITS_BY_SERVICE`, `V_CREDITS_BY_WAREHOUSE` | クレジットの使われ方 |

`alert_email`(検証済みのユーザーメール。git 管理対象外の `terraform.tfvars` に記載)を設定すると、メールアラートも作成されます: 1 時間に 3 回以上のログイン失敗、COPY エラー、月間クレジットが 60 超。アラートは `MONITOR_WH` で毎時実行されるため少額のコストがかかります。間隔は 60 分のままにしてください。

`ACCOUNT_USAGE` のデータは最大で数時間遅れます。リアルタイムには `INFORMATION_SCHEMA` のテーブル関数を使います。クラウドとの対応: これらのビュー ≈ CloudTrail + CloudWatch メトリクス / Cloud Audit Logs + Monitoring。

## 2. ID とネットワークの強化
`governance` は `NP_HANDSON`、`AP_HUMAN`(MFA 必須)、`SP_HUMAN`(アイドル 30 分)を作成し(**強制はしません**)、`AP_SERVICE`(鍵ペアのみ)も作成します。`AP_SERVICE` の `TERRAFORM` ユーザーへの適用は `scripts/apply-policies` が行います。

**CI([ガイド 08](08-ci-and-apply.md))を設定する場合、アカウントへの強制はスキップします。** `terraform.tfvars` と `TFVARS_JSON` のどちらでも、`enforce_account_policies` は `false` のままにしてください。このフラグは `NP_HANDSON` と `AP_HUMAN` をアカウント全体に適用します。アカウントの[ネットワークポリシー](https://docs.snowflake.com/en/user-guide/network-policies)は、より具体的なポリシーを持たないすべてのユーザー(`TERRAFORM` と plan 用ユーザーを含む)に適用されるため、GitHub ホストランナーがサインインできなくなります。スキップした場合、両ポリシーは適用されないままになります。すでに強制した場合は、ガイド 08 の前にフラグを `false` にして apply してください。

CI を**使わない**場合に限り、アカウントに強制します:
1. MFA が登録済みであることを確認してから、git 管理対象外の `terraform/envs/handson/terraform.tfvars` に `allowed_ips = ["<あなたのグローバル IP>/32"]` と `enforce_account_policies = true` を設定します。フラグを `-var` で渡さないでください。後でフラグなしの apply を実行すると、ポリシーが外れます。
2. 適用します:
```bash
source scripts/tf-env
terraform -chdir=terraform/envs/handson apply
```
テスト中は別の管理者セッションを開いたままにしてください。IP を間違えると締め出されます。

## 3. 監査と Trust Center
`sql/audit.sql` は、今週 HEALTH 列を読んだのは誰か、どの権限が変わったか、RAW のデータがどこへ流れるかに答えます。Snowsight の **Governance & security > Trust Center** で CIS ベンチマークのスキャナーを有効にし、検出結果を読み(セクション 2 を強制しない限り MFA/ネットワークポリシーの指摘は残ります。CI を使う場合はスキップします)、1 件を修正します。

## このステップ(監視)のコスト
約 4 クレジット(`MONITOR_WH` での毎時のアラートとクエリ)。

## 確認(監視)

```bash
snow sql -c handson_tf --warehouse MONITOR_WH -q "SELECT * FROM HANBIT_OPS.MONITORING.V_CREDITS_BY_SERVICE ORDER BY DAY DESC LIMIT 5"
snow sql -c handson_tf --warehouse MONITOR_WH -f sql/audit.sql
scripts/verify-step 07 --execute
```
クレジットのビューが行を返し、監査クエリにアクセスマトリクスの読み取りが表示されること(ACCOUNT_USAGE は最大数時間遅れるため、できたばかりのアカウントでは行がまだ出ないことがあります。その場合も確認ステップは成功します)。

## 4. FinOps: 請求に気づかれる前に数字を知る
```bash
scripts/cost-report            # サービス別クレジットを計画 53 / 警告 70 / 強制停止 80 と比較(70 以上は終了コード 2)
scripts/cost-guard --status    # リソースモニターとウェアハウス
scripts/cost-guard --suspend-all --execute
```
保護は安い順に重ねます。ウェアハウスの `auto_suspend = 60`、ウェアハウス単位のリソースモニター(`scripts/bootstrap` が作成し、`scripts/attach-monitors` が割り当て)、80 クレジットで強制停止するアカウントモニター `HANDSON_ACCOUNT_MONITOR`(`scripts/bootstrap` が作成)、そしてこのレポートです。`ACCOUNT_USAGE` は最大 3 時間ほど遅れるため、ウェアハウスについての本当のブレーキはレポートではなくモニターです。Seoul のレートを `scripts/preflight` で確認するまで、クレジット数は推定値です。

**モニターの対象外:** [リソースモニター](https://docs.snowflake.com/en/user-guide/resource-monitors)が扱うのはウェアハウスだけです。ガイド 05 のデータ品質チェック(レポートの `DATA_QUALITY_MONITORING`)、サーバーレスタスク、Snowpipe Streaming などのサーバーレス機能は、集計も停止もされません。`scripts/cost-report` の該当行を確認するか、[予算(budget)](https://docs.snowflake.com/en/user-guide/budgets)を追加してください。`scripts/cost-guard --suspend-all --execute` はウェアハウス、Dynamic Table、そのデータ品質チェックをサスペンドしますが、アラート、タスク、パイプは対象外です。再開方法はガイド 05 を参照してください。

## 5. 後片付け
`terraform destroy` は認証情報を `SNOWFLAKE_*` 変数から読み取りますが、`scripts/teardown` はそれらを読み込みません。リポジトリのルートで、すべて同じシェルで実行してください:
```bash
read -rs PRIVATE_KEY_PASSPHRASE && export PRIVATE_KEY_PASSPHRASE   # パスフレーズを入力して Enter
source scripts/tf-env                                              # Terraform が読む変数を export する
scripts/teardown               # プレビュー
scripts/teardown --execute --yes  # コンピュートをサスペンドし、terraform destroy、OPS DB・モニター(アカウントとウェアハウス)・TERRAFORM ユーザー・TF_ADMIN を削除
```
スクリプト内の `snow sql -c handson_admin` の手順は、その接続のユーザー、ロール、鍵をそのまま使います。破壊的な操作のため、`--execute` がなければプレビューのみで、`--execute` を付けても `--yes` なしでは実行を拒否します。完了後は、生成したローカルの `~/.snowflake/*.p8` 鍵も削除してください。

## このステップ(FinOps と後片付け)のコスト
0.5 クレジット未満。後片付けにより、継続的なコストはすべて止まります。

## 確認(FinOps と後片付け)

```bash
scripts/cost-report                                       # 合計クレジットと、計画 53 / 警告 70 / 停止 80 に対するステータス
scripts/cost-guard --status
# scripts/teardown --execute --yes の後(管理者用の鍵がまだあるうちに):
snow sql -c handson_admin -q "SHOW WAREHOUSES"            # LOAD_WH、TRANSFORM_WH、BI_WH、MONITOR_WH が残っていない
snow sql -c handson_admin -q "SHOW RESOURCE MONITORS"     # *_WH_MONITOR と HANDSON_ACCOUNT_MONITOR が残っていない
snow sql -c handson_admin -q "SHOW USERS LIKE 'TERRAFORM'"   # 行が返らない
```
後片付けの後は `handson_tf` 接続が使えなくなるため、これらの確認には `handson_admin` を使います。

---
<!-- nav:bottom -->
[🏠 7日間の流れ](../../../README.ja.md#7日間の流れ) · ← [06 BI と AI](06-bi-and-ai.md) · [08 CI と apply](08-ci-and-apply.md) →
<!-- /nav:bottom -->
