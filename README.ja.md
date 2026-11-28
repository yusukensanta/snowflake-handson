# Snowflake ハンズオン: 保険・金融編

[English: README.md](README.md)

架空の保険・消費者金融グループを題材に、**セキュリティとガバナンスを備えたエンドツーエンドのデータパイプライン**を、
**トライアル予算 $400 以内**で構築しながら Snowflake を学びます。AWS や GCP などの経験があるデータエンジニア向けで、
Snowflake の概念を既知のクラウドの概念に対応づけて説明します。

## 作るもの
合成ソースデータ → 取り込み(バッチと Snowpipe Streaming) → RAW → Dynamic Tables による整形 →
Iceberg v3 テーブルとマート → Streamlit による BI と AI。**列・行・ロール単位のアクセス制限**を自動アクセステストで検証し、
監視、FinOps、後片付け(teardown)まで扱います。

## 7日間の流れ
| 日 | ガイド | 内容 |
|---|---|---|
| 1 | [00 概要](docs/ja/guides/00-orientation.md)、[01 セットアップ](docs/ja/guides/01-setup-and-guardrails.md)、[02 RBAC と Terraform](docs/ja/guides/02-rbac-and-terraform.md) | 概要、まずコスト防御、RBAC、Terraform、import ラボ |
| 2 | [03 データ取り込み](docs/ja/guides/03-ingestion.md) | データ取り込み |
| 3 | [05 変換と Iceberg](docs/ja/guides/05-transform-and-iceberg.md)(前半) | CURATED への変換(ポリシーは CURATED に付けるため先に行う) |
| 4-5 | [04 ガバナンス](docs/ja/guides/04-governance.md) | ガバナンス: タグ、マスキング、行アクセス、アクセステスト |
| 5 | [05 変換と Iceberg](docs/ja/guides/05-transform-and-iceberg.md)(後半) | Iceberg v3 |
| 6 | [06 BI と AI](docs/ja/guides/06-bi-and-ai.md) | BI と AI |
| 7 | [07 監視と FinOps](docs/ja/guides/07-monitoring-finops-teardown.md) | 監視、FinOps、teardown |
| 7+ | [08 CI と apply](docs/ja/guides/08-ci-and-apply.md) | CI と GitHub Actions からの apply |
| 任意 | [付録 AWS](docs/ja/guides/appendix-aws.md) | 自分の S3 バケット |

## コスト
計画は約 53 クレジット($4.50 換算で約 $240)、予備約 20、リソースモニターのハードストップは 80 クレジットです
(対象はウェアハウスのみで、サーバーレス機能は含まれません。[ガイド 07](docs/ja/guides/07-monitoring-finops-teardown.md) を参照)。
詳細は [ガイド 00](docs/ja/guides/00-orientation.md) を参照してください。

## セキュリティの最低ライン
アカウント ID、パスワード、トークン、鍵、Terraform の state など機密情報は一切コミットしません。
コミット前に `scripts/check-secrets` を実行してください。

## はじめかた
`scripts/install-tools --execute && scripts/preflight` を実行し、ガイド 01 に進みます。

## 現状と免責
- **オフラインでのテスト済み、実環境での通しの検証は未了です。** ユニットテスト、リンター、`terraform validate`、CI は通っていますが、
  すべてのガイドを実際の Snowflake アカウントで最後まで実行したわけではありません。エディションやリージョンに依存する機能
  (Cortex、マネージド Iceberg ストレージ、セマンティックビュー、Snowpipe Streaming)は構文や提供状況が異なる場合があります。確認方法は各ガイドに記載しています。
- **費用はご自身の負担です。** クレジットの数値は $4.50/クレジットを仮定した見積もりです。`scripts/preflight` で実際の単価を確認し、
  リソースモニターを維持し、使わないときは `scripts/cost-guard --suspend-all --execute` を実行してください。
- 企業・人物・データはすべて**架空の合成データ**です。Snowflake Inc. とは無関係で、同社の承認を受けたものではありません。Snowflake は同社の商標です。

## ライセンスとコントリビュート
[MIT](LICENSE)。[CONTRIBUTING.md](CONTRIBUTING.md) と [SECURITY.md](SECURITY.md) を参照してください。

## 質問と共有
[Discussions](https://github.com/yusukensanta/snowflake-handson/discussions) を使ってください。質問は Q&A、ガイドの提案は Ideas、使ってみた報告は Show and tell
(エディション、リージョン、進んだところ、実際に使ったクレジット)へ。不具合やドキュメント修正は Issue か Pull Request へお願いします。
日本語でも英語でも OK です。アカウント ID や認証情報は絶対に投稿しないでください。
