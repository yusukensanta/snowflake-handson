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
`governance` は `NP_HANDSON`、`AP_HUMAN`(MFA 必須)、`SP_HUMAN`(アイドル 30 分)を作成し(**強制はしません**)、`AP_SERVICE`(鍵ペアのみ)を `TERRAFORM` ユーザーに適用します。アカウントに強制するには:
1. `allowed_ips = ["<あなたのグローバル IP>/32"]` を設定し、MFA が登録済みであることを確認します。
2. `terraform apply -var enforce_account_policies=true` を実行します。
テスト中は別の管理者セッションを開いたままにしてください。IP を間違えると締め出されます。

## 3. 監査と Trust Center
`sql/audit.sql` は、今週 HEALTH 列を読んだのは誰か、どの権限が変わったか、RAW のデータがどこへ流れるかに答えます。Snowsight の **Governance & security > Trust Center** で CIS ベンチマークのスキャナーを有効にし、検出結果を読み(セクション 2 を強制するまでは MFA/ネットワークポリシーの指摘が出ます)、1 件を修正します。

## このステップ(監視)のコスト
約 4 クレジット(`MONITOR_WH` での毎時のアラートとクエリ)。

## 確認(監視)
`SELECT * FROM HANBIT_OPS.MONITORING.V_CREDITS_BY_SERVICE ORDER BY DAY DESC LIMIT 5;` が行を返し、監査クエリにアクセスマトリクスの読み取りが表示されること。

## 4. FinOps: 請求に気づかれる前に数字を知る
```bash
scripts/cost-report            # サービス別クレジットを計画 53 / 警告 70 / 強制停止 80 と比較(70 以上は終了コード 2)
scripts/cost-guard --status    # ウェアハウス、モニター、Dynamic Table
scripts/cost-guard --suspend-all
```
保護は安い順に重ねます。ウェアハウスの `auto_suspend = 60`、ウェアハウス単位のリソースモニター(Terraform の `finops`)、80 クレジットで強制停止するアカウントモニター `HANDSON_ACCOUNT_MONITOR`(`scripts/bootstrap` が作成)、そしてこのレポートです。`ACCOUNT_USAGE` は最大 3 時間ほど遅れるため、本当のブレーキはレポートではなくモニターです。Seoul のレートを `scripts/preflight` で確認するまで、クレジット数は推定値です。

## 5. 後片付け
```bash
scripts/teardown --dry-run     # プレビュー
scripts/teardown --yes         # コンピュートをサスペンドし、terraform destroy、OPS DB・モニター・TERRAFORM ユーザー・TF_ADMIN を削除
```
破壊的な操作のため、`--yes` なしでは実行を拒否します。完了後は、生成したローカルの `~/.snowflake/*.p8` 鍵も削除してください。

## このステップ(FinOps と後片付け)のコスト
0.5 クレジット未満。後片付けにより、継続的なコストはすべて止まります。

## 確認(FinOps と後片付け)
`scripts/cost-report` が合計とステータスを表示すること。後片付け後は `SHOW WAREHOUSES` に自分たちのウェアハウスが残っていないこと。

---
<!-- nav:bottom -->
[🏠 7日間の流れ](../../../README.ja.md#7日間の流れ) · ← [06 BI と AI](06-bi-and-ai.md) · [08 CI と apply](08-ci-and-apply.md) →
<!-- /nav:bottom -->
