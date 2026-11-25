# 01 · セットアップとガードレール

<!-- nav:top -->
[🏠 7日間の流れ](../../../README.ja.md#7日間の流れ) · ← [00 概要](00-orientation.md) · [02 RBAC と Terraform](02-rbac-and-terraform.md) →
<!-- /nav:top -->

**English:** [../../guides/01-setup-and-guardrails.md](../../guides/01-setup-and-guardrails.md)

順序が重要です: ツール → 接続 → preflight → ガードレール(リソースモニター) → コンピュートを使う作業。

## 1. ツールのインストール
```bash
scripts/install-tools --dry-run   # 実行計画を確認
scripts/install-tools             # terraform, snow (SnowCLI), shellcheck, gitleaks。再実行しても安全
```

## 2. 管理者接続の作成(鍵ペア)
Google サインインで作成したものを含め、トライアルアカウントには SSO の IdP がありません。そのため `authenticator = "EXTERNALBROWSER"` は
エラー 390190 で失敗し、CLI は Google や Snowsight のブラウザログインを再利用できません。代わりに鍵ペアを使います。
1. トライアルのユーザーで Snowsight にサインインし、ブラウザログインの MFA を有効にします(表示されれば プロフィール > Authentication)。
2. 暗号化した鍵を生成します。鍵は `~/.snowflake/` に置き、リポジトリには入れません。パスフレーズは聞かれたときに決めます:
   ```bash
   mkdir -p ~/.snowflake && chmod 700 ~/.snowflake
   openssl genrsa 2048 | openssl pkcs8 -topk8 -v2 aes256 -inform PEM -out ~/.snowflake/handson_admin_key.p8
   openssl rsa -in ~/.snowflake/handson_admin_key.p8 -pubout -out ~/.snowflake/handson_admin_key.pub
   chmod 600 ~/.snowflake/handson_admin_key.p8
   grep -v -- '-----' ~/.snowflake/handson_admin_key.pub | tr -d '\n'   # 公開鍵を 1 行で表示(次の手順で使用)
   ```
3. Snowsight の SQL ワークシート(**Projects > Worksheets > + > SQL Worksheet**、ロールは `ACCOUNTADMIN`)で `SELECT CURRENT_USER();` を実行し、
   鍵を登録します。名前は表示されたとおりに引用符で囲んでください。Google サインインのユーザーは小文字で、引用符なしだと大文字に変換され
   `User '...' does not exist or not authorized` で失敗します:
   ```sql
   ALTER USER "<CURRENT_USER() の値>" SET RSA_PUBLIC_KEY='<1 行の公開鍵>';
   DESC USER "<CURRENT_USER() の値>";   -- LOGIN_NAME を控える。RSA_PUBLIC_KEY_FP が設定されているはず
   ```
   有効期限を設定できる名前付きの形式 `ALTER USER ... ADD KEY PAIR` もあります。
   [鍵ペア認証のドキュメント](https://docs.snowflake.com/en/user-guide/key-pair-auth)を参照してください。
4. `config/connections.toml.example` を `~/.snowflake/connections.toml` にコピーし、`<org>-<account>` を設定し、`user` には手順 3 の
   `LOGIN_NAME`(多くはメールアドレスで、`CURRENT_USER()` の表示と異なる場合があります)を設定して `chmod 600` します。
5. このシェルでのみ有効なパスフレーズを CLI に渡し(どこにも保存しません)、テストします:
   ```bash
   read -rs "PRIVATE_KEY_PASSPHRASE?Key passphrase: " && echo && export PRIVATE_KEY_PASSPHRASE   # zsh。bash では read -rsp 'Key passphrase: ' PRIVATE_KEY_PASSPHRASE
   snow connection test -c handson_admin
   ```
   `Status | OK` とロール `ACCOUNTADMIN` が表示されれば成功です。新しいターミナルを開くたびにパスフレーズを再度エクスポートしてください。

| エラー | 原因と対処 |
|---|---|
| `390190 ... SAML Identity Provider account parameter` | プロファイルが `EXTERNALBROWSER` で、アカウントに SSO がない。上記のとおり `SNOWFLAKE_JWT` に変更 |
| `Encrypted private key, you must provide the passphrase` | このシェルで `PRIVATE_KEY_PASSPHRASE` をエクスポートする |
| `User '...' does not exist or not authorized` | `CURRENT_USER()` の表示どおりの大文字小文字で引用符を付け、ロールは `ACCOUNTADMIN` にする |
| CLI で JWT や "user not found" | `user` を `DESC USER` の `LOGIN_NAME` にする |

実ファイルはリポジトリ外にあり、git の管理対象外です。この管理者の鍵は長期間有効な `ACCOUNTADMIN` の認証情報です。bootstrap と teardown の後に
`ALTER USER "<name>" UNSET RSA_PUBLIC_KEY;` を実行し、`~/.snowflake/handson_admin_key.*` を削除してください。
**クラウドとの対応:** パスフレーズで保護した静的キーを使う AWS CLI プロファイルに相当し、Terraform 用のサービス ID(ガイド 02)はワークロード用 IAM ロールに相当します。

## 3. preflight の実行
```bash
scripts/preflight --dry-run
scripts/preflight
```
ツール、接続、リージョン、エディション、Cortex のクロスリージョン設定(読み取りのみで変更しません)、Snowflake 管理ストレージでの Iceberg の可否(一時テーブルを作成して削除)を確認し、Snowsight(Admin > Cost Management)に表示される実際のクレジット単価の入力を求めます。

| 結果 | 意味 | 代替策 |
|---|---|---|
| edition が `block` | ポリシーには Enterprise が必要 | Enterprise のトライアルを使う |
| iceberg が `warn` | Snowflake ストレージが使えない | Iceberg は概念説明と付録のみにする |
| cortex が `warn` | CoCo/Cortex が使えない可能性 | AI ラボをスキップし、リージョン内にとどまる(クロスリージョン推論は使わない) |

**確認結果(記入、アカウント ID は伏せる):** リージョン ___、エディション ___、単価 ___、Iceberg プローブ ___、Cortex ___。

## このステップのコスト
約 0.1 クレジット(プローブ用に XS ウェアハウスを数秒使用)。

## 確認
`scripts/preflight` が終了コード 0 で終わり、`block` の行が出ないこと。

## 4. ワークロードの前にガードレール
```bash
scripts/bootstrap --dry-run      # 実行される SQL をすべて表示(何も実行しない)
scripts/bootstrap --quota 80     # アカウントのリソースモニター、TF_ADMIN ロール、TERRAFORM サービスユーザーと鍵ペア
scripts/cost-guard --status
```
- **アカウントのリソースモニター** `HANDSON_ACCOUNT_MONITOR`: 上限 80 クレジット、50/75/90 % で通知、95 % でサスペンド、100 % で `SUSPEND_IMMEDIATE`。設定には `ACCOUNTADMIN` が必要なので、Terraform ではなくスクリプトが作成します。
- **88 ではなく 80 にする理由:** $4.50/クレジットなら $400 は約 88 クレジットです。差分は、モニターが作動した後に課金されるクレジットに対する安全マージンです。実際の単価で再計算し、約 10 % を引いてください。
- **サービス ID:** ユーザー `TERRAFORM`(`TYPE = SERVICE`、鍵ペアのみ、パスワードなし)とロール `TF_ADMIN`。Terraform に必要なアカウント権限だけを持ちます。秘密鍵は `PRIVATE_KEY_PASSPHRASE` のパスフレーズ(管理者鍵用にエクスポートしたものと同じなので、1 回の export で両方の接続を使えます。未設定だと bootstrap は実行を拒否します)で暗号化され、`~/.snowflake/` に置かれ、リポジトリには入りません。Terraform 実行時も `PRIVATE_KEY_PASSPHRASE` を export したままにします。
- **ウェアハウスのモニター**(Terraform の `finops` モジュール): ウェアハウスごとに 1 つ。75/90 % で通知、100 % でサスペンド。
- **緊急停止:** `scripts/cost-guard --suspend-all`。

クラウドとの対応: リソースモニターは AWS Budgets のアクションや GCP の予算+Pub/Sub による停止に近いですが、プラットフォーム自身が強制します。

## このステップのコスト(続き)
0 クレジット。モニターとロールはメタデータのみです。

## 確認(ガードレール)
`scripts/cost-guard --status` に、上限 80 の `HANDSON_ACCOUNT_MONITOR` が表示されること。

---
<!-- nav:bottom -->
[🏠 7日間の流れ](../../../README.ja.md#7日間の流れ) · ← [00 概要](00-orientation.md) · [02 RBAC と Terraform](02-rbac-and-terraform.md) →
<!-- /nav:bottom -->
