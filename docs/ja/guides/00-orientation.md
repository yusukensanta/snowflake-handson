# 00 · 概要

<!-- nav:top -->
[🏠 7日間の流れ](../../../README.ja.md#7日間の流れ) · [01 セットアップ](01-setup-and-guardrails.md) →
<!-- /nav:top -->

**対象読者:** AWS/GCP などの経験があり、Snowflake は初めてのデータエンジニア。
**題材:** Hanbit Insurance & Capital(架空): 引受、保険金請求(健康情報)、融資(信用情報)、経理、リスク/不正、マーケティング。
**English:** [../../guides/00-orientation.md](../../guides/00-orientation.md)

## 既知のクラウド概念との対応
| Snowflake | 近い概念 | 主な違い |
|---|---|---|
| アカウント / リージョン | クラウドのプロジェクト/アカウント | 1 つのアカウントに全データベースとコンピュートが入る |
| 仮想ウェアハウス | 一時的なクエリクラスタ(EMR, Dataproc) | 稼働中は秒単位課金。積極的にサスペンドする |
| データベース / スキーマ | データセット / カタログ | 権限はこれらのオブジェクトに付与する |
| ロール(RBAC) | IAM ロール | ユーザーはロールを持ち、権限はロールにだけ付与する |
| タグ + マスキングポリシー | Lake Formation / BigQuery ポリシータグ | ポリシーをタグに紐づけるのでスケールする |
| 行アクセスポリシー | 行レベルセキュリティ | マッピングテーブル駆動。アクセスはコードでなくデータ |
| ストレージ統合 | IAM ロールの信頼設定 | 本編では不要(付録を参照) |

## セキュリティの最低ライン(このリポジトリ自体が実践例です)
- アカウント ID、パスワード、トークン、鍵、Terraform の state はコミットしません。テンプレートは `*.example` です。
- サービスユーザーは鍵ペア認証、人間のユーザーはブラウザで MFA。`ACCOUNTADMIN` は初期設定のみに使い、短期間だけ使う鍵ペアの管理者接続を
  teardown で削除します(ガイド 01)。
- データは合成で再現可能(シード固定)。ID 番号はチェックディジットを意図的に不正にし、実在の人物と一致しません。
- コミット前に `scripts/check-secrets` を実行します。

## コスト計画(クレジット。$4.50/クレジットと仮定し、実際のレートは 1 日目に確認)
| 項目 | クレジット |
|---|---|
| セットアップ、Terraform、ポリシーテスト | 4 |
| データ取り込み | 8 |
| 変換 | 8 |
| BI | 8 |
| ガバナンス | 6 |
| 監視 | 4 |
| CoCo / Cortex(1日の上限あり) | 15 |
| **計画合計** | **約 53** |
| 予備 / ハードストップ | 約 20 / 80 |

ガードレール(リソースモニター、auto-suspend 60 秒)は、**どのワークロードより先に**作成します。

## 毎回のセッション開始時
新しいターミナルでは毎回、鍵のパスフレーズが必要です。Terraform のコマンドには `scripts/tf-env` も必要です。スクリプトは、ガイドが `handson_admin`(`ACCOUNTADMIN`: bootstrap、`attach-monitors`、後片付け)と指定しない限り、`handson_tf` 接続(ロール `TF_ADMIN`)を使います。
```bash
cd snowflake-handson
read -rs "PRIVATE_KEY_PASSPHRASE?Key passphrase: " && echo && export PRIVATE_KEY_PASSPHRASE   # zsh。bash では: read -rsp 'Key passphrase: ' PRIVATE_KEY_PASSPHRASE; echo; export PRIVATE_KEY_PASSPHRASE
source scripts/tf-env      # terraform コマンドの前だけ(ガイド 02、04、05、07)
```
各ガイドの末尾には**確認**ブロックがあり、実行するコマンド、期待する結果、Snowsight で同じ状態を見る場所を示します。`scripts/verify-step N` は読み取り専用のチェックを実行し、結果を `.progress/state.json` に記録します。

## このステップのコスト
0 クレジット(読むだけ)。

## 確認

```bash
scripts/verify-step 00        # scripts/check-secrets を実行します(Snowflake には接続しません)
cat .progress/state.json      # 確認済みの各ステップの UTC 時刻
```
`[check-secrets] clean` に続いて `[info] step 00 verified; recorded in .progress/state.json` と表示されること。

---
<!-- nav:bottom -->
[🏠 7日間の流れ](../../../README.ja.md#7日間の流れ) · [01 セットアップ](01-setup-and-guardrails.md) →
<!-- /nav:bottom -->
