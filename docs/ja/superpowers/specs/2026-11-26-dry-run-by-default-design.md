# スクリプトは既定でドライラン

**English:** [../../../superpowers/specs/2026-11-26-dry-run-by-default-design.md](../../../superpowers/specs/2026-11-26-dry-run-by-default-design.md)

## 意図
スクリプトは、中身を詳しく読まずに実行されることがあります。何かを変更するスクリプトは、既定ではプレビューのみを行い、
明示的な `--execute` がある場合にだけ実行しなければなりません。

## 目標 / 非目標
- 目標: `--execute` なしでは、Snowflake、GitHub、マシン、リポジトリのファイルを一切変更しないこと。
- 目標: 読み取り専用のチェックは、フラグなしで引き続き実際の結果を返すこと。
- 非目標: `terraform`、`snow`、`python -m ...` の直接呼び出しを防ぐこと。
- アンチ目標: 完了した操作と取り違えられるプレビュー。

## アプローチ
1. **`scripts/lib/common.sh` で既定値を反転する(採用)。** シェルスクリプトが 1 つの実装を共有し、
   読み取り専用のスクリプトは明示的に対象外にします。
2. 安全策を追加するラッパー: スクリプトを直接呼び出すと回避されてしまいます。
3. スクリプトごとに個別のフラグ実装: 重複し、実装がずれていきやすくなります。

## 動作

| スクリプト | フラグなし | `--execute` |
|---|---|---|
| `bootstrap`、`apply-curated`、`apply-policies`、`attach-monitors`、`load-batch`、`stream-load`、`setup-github`、`install-tools`、`gen-data` | プレビュー | 実行 |
| `sync_doc_nav.py` | 変更されるファイルを一覧表示(`--check` は変更なし) | ファイルを書き込む |
| `teardown` | プレビュー | `--yes` を併せて指定した場合にのみ実行 |
| `cost-guard --suspend-all` | プレビュー(何もサスペンドしない) | サスペンドする |
| `preflight` | 読み取り専用のチェックを実行。Iceberg のプローブは表示のみ | プローブも実行 |
| `verify-step` | チェックを実行。進捗は記録しない | チェックを実行して記録 |
| `check-secrets`、`access-matrix`、`cost-report`、`cost-guard --status`、`open-read` | これまでどおり実行 | 不要 |
| `tf-env` | 変更なし | 不要 |

- 変更を有効にするのは `--execute` 引数だけです。エクスポートされた `DRY_RUN=0` では有効になりません。
- `--dry-run` は引き続き受け付けます。`--execute` と組み合わせるとエラーです(終了コード 64)。
- プレビューは、何も変更されていないことと実行方法を示す行で終わります。
- 他のスクリプトを呼び出すスクリプトは、`--execute` を明示的に引き渡します(`teardown` から `cost-guard`)。

## あわせて更新するもの
英語と日本語のガイドと README、`CONTRIBUTING.md`、`CLAUDE.md`、`.claude/commands` と `.claude/skills`、
およびスクリプトや `sfops` が出力する「次の手順」や「これを実行」のすべてのメッセージ。

## 検証
テストは、偽の `snow`、`gh`、`uv` とインストール用コマンドを使って各スクリプトを実行し、`--execute` なしでは
変更を伴うコマンドが一切呼ばれないことを確認します。

## 実装者に任せる事項
ヘルパー関数名、プレビューの文言、テストの構成。
