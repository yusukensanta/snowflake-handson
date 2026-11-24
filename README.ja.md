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
| 1 | [00](docs/ja/guides/00-orientation.md), 01, 02 | 概要、まずコスト防御、RBAC、Terraform、import ラボ |
| 2 | 03 | データ取り込み |
| 3 | [05](docs/ja/guides/05-transform-and-iceberg.md) 前半 | CURATED への変換(ポリシーは CURATED に付けるため先に行う) |
| 4-5 | 04 | ガバナンス: タグ、マスキング、行アクセス、アクセステスト |
| 5 | 05 後半 | Iceberg v3 |
| 6 | 06 | BI と AI |
| 7 | 07 | 監視、FinOps、teardown |
| 7+ | [08](docs/ja/guides/08-ci-and-apply.md) | CI と GitHub Actions からの apply |
| 任意 | [付録](docs/ja/guides/appendix-aws.md) | 自分の S3 バケット |

## コスト
計画は約 53 クレジット($4.50 換算で約 $240)、予備約 20、リソースモニターのハードストップは 80 クレジットです。
詳細は [ガイド 00](docs/ja/guides/00-orientation.md) を参照してください。

## セキュリティの最低ライン
アカウント ID、パスワード、トークン、鍵、Terraform の state など機密情報は一切コミットしません。
コミット前に `scripts/check-secrets` を実行してください。

## はじめかた
`scripts/install-tools && scripts/preflight` を実行し、ガイド 01 に進みます。
