# 既定でドライラン 実装計画

**English:** [../../../superpowers/plans/2026-11-26-dry-run-by-default.md](../../../superpowers/plans/2026-11-26-dry-run-by-default.md)

> **エージェント作業者向け:** 必須サブスキル: この計画をタスクごとに実装するには、superpowers:subagent-driven-development(推奨)または superpowers:executing-plans を使用してください。手順の進捗管理にはチェックボックス(`- [ ]`)記法を使います。

**ゴール:** 何かを変更するスクリプトは既定でプレビューのみを行い、`--execute` がある場合にだけ実行します。読み取り専用のチェックは、フラグなしで引き続き動作します。

**アーキテクチャ:** `scripts/lib/common.sh` がプレビューを既定にし、読み取り専用を明示的に指定する手段を提供します。各スクリプトは、すべての副作用とすべての「実行した」というメッセージにそのヘルパーを使います。動作は、一時サンドボックス内で偽の外部ツールを使い、スクリプトのコピーを実行して確認します。

**技術スタック:** bash、Python 3.15.2(uv)、pytest、shellcheck。

**仕様:** `docs/superpowers/specs/2026-11-26-dry-run-by-default-design.md`([日本語版](../specs/2026-11-26-dry-run-by-default-design.md))

## 全体の制約

- `--execute` なしでは、Snowflake、GitHub、マシン、リポジトリのファイルを一切変更しない。
- 変更を有効にするのは `--execute` 引数だけ。エクスポートされた `DRY_RUN=0` では有効にならない。
- `--dry-run` は引き続き受け付ける。`--execute` と組み合わせるとエラー(終了コード 64)。
- プレビューは、何も変更されていないことと実行方法を示す行で終わる。文言は正確に `[preview] nothing was changed. Re-run with <hint> to apply.`(`<hint>` は `--execute`、`teardown` では `--execute --yes`)。
- プレビューは、完了した操作と読めるメッセージを決して出力しない。
- 不明な引数は終了コード 64。
- スクリプトは冪等性を保ち、`scripts/lib/common.sh` を source し(`tf-env` を除く)、shellcheck を通す。`tf-env` は変更しない。
- ドキュメントは 2 言語: `docs/guides` と `docs/ja/guides`(`README.md` と `README.ja.md`)を一緒に変更する。コマンドは翻訳しない。
- 2026-11-25 の仕様と計画(履歴)、および `terraform/`(そこの説明はスクリプト名を挙げるだけで、`.tf` を変更すると plan ワークフローが起動する)は編集しない。
- 所有者に依頼されない限り、コミットもプッシュもしない。依頼された場合はブランチ + PR とし、`main` には決してプッシュしない。
- 実装中は、実際のリポジトリで `--execute` を付けてスクリプトを実行しない(本番アカウントに到達する可能性がある)。唯一の例外は、ローカルファイルを書き出すタスク 5 の `scripts/gen-data --execute --emit-*`。

## レビューの重点

1. 以前の習慣の `scripts/teardown --yes`: プレビューのみで、何も破棄しない(タスク 2)。
2. フラグや打ち間違いを渡された `scripts/check-secrets`: スキャンせずに `clean` と出力することは決してない。現状の `check-secrets --dry-run` は、フラグがディレクトリとして読まれるため、まさにそうなる(タスク 1)。
3. シェルでエクスポートされた `DRY_RUN=0` や `PRINT_ONLY=1`: 動作は影響を受けない(タスク 1)。
4. 打ち間違いの `--exceute`: 終了コード 64 で何も実行しない。現状で不明な引数を無視するスクリプトも含む(タスク 1-3)。
5. プレビュー出力に "done"、"ready"、"generating"、"added" がないこと(タスク 3)。

---

### タスク 1: 共有フラグ、テスト用サンドボックス、読み取り専用スクリプトと cost-guard

**ファイル:**
- 変更: `scripts/lib/common.sh`、`scripts/access-matrix`、`scripts/cost-report`、`scripts/open-read`、`scripts/check-secrets`、`scripts/cost-guard`
- 作成: `tests/conftest.py`、`tests/test_script_flags.py`
- 変更: `tests/test_cost_guard.py`(`--execute` を渡す)

**インターフェース:**
- `common.sh` が提供するもの(グローバル変数はすべて無条件に代入し、環境変数からは決して取り込まない):
  - `parse_common_flags "$@"`: `DRY_RUN`(`--execute` がなければ 1)、`PRINT_ONLY`(`--dry-run` がある場合のみ 1)、`REST_ARGS` を設定する。両方のフラグがあれば終了コード 64。終了ステータスが 0 かつ `DRY_RUN=1` のときにプレビュー行を出力する EXIT トラップを設定する。
  - `mark_read_only`: そのトラップを解除する。以降、読み取り専用のコードは `DRY_RUN` ではなく `PRINT_ONLY` で分岐する。
  - `PREVIEW_HINT`(既定値 `--execute`): トラップが参照する。
  - `done_msg MSG`: `DRY_RUN=0` のときだけ `log_info` する。常に 0 を返す。
  - `run CMD...`: 変更なし。
  - `require_cmd` のメッセージは `(run scripts/install-tools --execute)` にする。
- `conftest.py` が提供するもの: 次を持つオブジェクトを返すフィクスチャ `sandbox`
  - `repo: Path`、`home: Path`: `tmp_path` 配下の `scripts/` と `sql/` のコピーと `data/out/claims.csv.gz`
  - `run(script: str, *args: str, env: dict[str, str] | None = None, stdin: str = "") -> subprocess.CompletedProcess[str]`
  - `calls() -> list[str]`: 偽ツールの呼び出しごとに 1 つの `"tool arg1 arg2 ..."`
  - `snapshot() -> dict[str, bytes]`: 呼び出しログを除く、`repo` と `home` 配下のすべてのファイルとディレクトリ
  - `fake(name: str, body: str = "") -> None`、`unfake(name: str) -> None`
  - 既定の偽ツール: `snow gh uv mise terraform openssl shellcheck gitleaks`。`snow` は、`SHOW WAREHOUSES` には `STARTED` のウェアハウス `TRANSFORM_WH` を 1 つ、`SHOW DYNAMIC TABLES...` には `ACTIVE` のテーブルを 1 つ、`COUNT(*) AS N` を含むクエリには `[{"N":0}]`、それ以外には `[]` を返す。`gh` は `repo view` に `o/r`、`api user` に `me`、`api users/me` に `1` を返す。
  - 子プロセスの環境は一から組み立てる: `PATH=<fakebin>:/usr/bin:/bin`、`HOME`、`FAKE_LOG`、および `env`。何も引き継がないため、実際の認証情報やツールには到達できない。

- [ ] **手順 1: フィクスチャと失敗するテストを書く**(`tests/test_script_flags.py`)

```python
@pytest.mark.parametrize("script", ["access-matrix", "cost-report", "open-read", "check-secrets", "cost-guard"])
def test_execute_with_dry_run_is_rejected(sandbox, script):
    r = sandbox.run(script, "--execute", "--dry-run")
    assert r.returncode == 64 and sandbox.calls() == []

@pytest.mark.parametrize("args", [(), ("--execute",)])
def test_read_only_scripts_really_run(sandbox, args):
    r = sandbox.run("cost-report", *args)
    assert r.returncode == 0 and "[preview]" not in r.stdout
    assert sandbox.calls() == ["uv run python -m sfops.cost"]

def test_status_runs_without_a_flag(sandbox):
    r = sandbox.run("cost-guard")
    assert any("SHOW RESOURCE MONITORS" in c for c in sandbox.calls()) and "[preview]" not in r.stdout

@pytest.mark.parametrize("env", [{}, {"DRY_RUN": "0"}, {"PRINT_ONLY": "1"}])
def test_suspend_all_previews_whatever_the_environment_says(sandbox, env):
    r = sandbox.run("cost-guard", "--suspend-all", env=env)
    assert r.returncode == 0 and sandbox.calls() == []
    assert "nothing is suspended" in r.stdout
    assert r.stdout.rstrip().endswith("[preview] nothing was changed. Re-run with --execute to apply.")

@pytest.mark.parametrize("arg", ["--dry-run", "--exceute", "/no/such/dir"])
def test_check_secrets_never_reports_clean_without_scanning(sandbox, arg):
    r = sandbox.run("check-secrets", arg)
    assert "clean" not in r.stdout
    assert r.returncode == (0 if arg == "--dry-run" else 64)

def test_check_secrets_still_scans_with_execute(sandbox):
    (sandbox.repo / "leak.txt").write_text("password" + ' = "hunter2hunter2"\n')
    assert sandbox.run("check-secrets", "--execute").returncode == 1

def test_open_read_rejects_unknown_argument(sandbox):
    assert sandbox.run("open-read", "--exceute").returncode == 64 and sandbox.calls() == []
```

`tests/test_cost_guard.py` では、`run_guard` が `--suspend-all` の前に `--execute` を渡すようにします。

- [ ] **手順 2: 実行して失敗を確認する**

実行: `uv run pytest tests/test_script_flags.py tests/test_cost_guard.py -q`
期待結果: FAIL(たとえば 64 ではなく終了コード 0、`check-secrets --dry-run` が `clean` を出力する)。

- [ ] **手順 3: `common.sh` のヘルパーを**上記のインターフェースどおりに**実装する。**

- [ ] **手順 4: スクリプトを変換する**
  - `access-matrix`、`cost-report`、`open-read`: `parse_common_flags` の後に `mark_read_only`。`PRINT_ONLY` で分岐する。
  - `open-read`: 残った引数があれば終了コード 64。
  - `check-secrets`: `common.sh` を source し、同じ 2 つを呼び出す。残る引数は最大 1 つで、`-` で始まらず、実在するものだけを受け付け、それ以外は終了コード 64。`PRINT_ONLY=1` のときは `[dry-run] would scan <root>` を出力して終了コード 0。
  - `cost-guard`: ステータスモードでは `mark_read_only` し、`show_json` は `PRINT_ONLY` で分岐する。サスペンドのプレビューは `[dry-run] would suspend every started warehouse and active Dynamic Table; nothing is suspended` を出力して終了コード 0。
  - 各 `Usage:` コメントを更新する。

- [ ] **手順 5: 確認する**

実行: `uv run pytest tests/test_script_flags.py tests/test_cost_guard.py -q && bash tests/test_check_secrets.sh && find scripts tests -type f \( -perm -u+x -o -name "*.sh" \) | xargs shellcheck`
期待結果: すべて成功、`PASS: check-secrets`、shellcheck の出力なし。

---

### タスク 2: teardown、preflight、verify-step

**ファイル:**
- 変更: `scripts/teardown`、`scripts/preflight`、`scripts/verify-step`
- 作成: `tests/test_script_mixed.py`

**インターフェース:**
- 利用するもの: タスク 1 のヘルパーと `sandbox`。

- [ ] **手順 1: 失敗するテストを書く**

```python
@pytest.mark.parametrize("args", [(), ("--yes",), ("--dry-run",)])
def test_teardown_previews_without_execute(sandbox, args):
    r = sandbox.run("teardown", *args)
    assert r.returncode == 0 and sandbox.calls() == []
    assert "Re-run with --execute --yes to apply." in r.stdout and "done." not in r.stdout

def test_teardown_execute_needs_yes(sandbox):
    assert sandbox.run("teardown", "--execute").returncode == 1 and sandbox.calls() == []

def test_teardown_execute_suspends_then_destroys(sandbox):
    r = sandbox.run("teardown", "--execute", "--yes")
    calls = sandbox.calls()
    assert r.returncode == 0, r.stderr
    suspend = next(i for i, c in enumerate(calls) if "ALTER WAREHOUSE" in c and "SUSPEND" in c)
    destroy = next(i for i, c in enumerate(calls) if c.startswith("terraform") and "destroy" in c)
    assert suspend < destroy and any("DROP ROLE IF EXISTS TF_ADMIN" in c for c in calls)

def test_preflight_default_reads_but_does_not_probe(sandbox):
    r = sandbox.run("preflight", stdin="\n")
    calls = "\n".join(sandbox.calls())
    assert "SELECT CURRENT_REGION()" in calls and "CREATE" not in calls and "DROP" not in calls
    assert "would run: CREATE DATABASE IF NOT EXISTS PREFLIGHT_SCRATCH" in r.stdout

def test_preflight_execute_probes(sandbox):
    sandbox.run("preflight", "--execute", stdin="\n")
    assert any("PREFLIGHT_SCRATCH" in c for c in sandbox.calls())

def test_preflight_dry_run_and_typo_touch_nothing(sandbox):
    assert sandbox.run("preflight", "--dry-run").returncode == 0
    assert sandbox.run("preflight", "--exceute").returncode == 64
    assert sandbox.calls() == []

def test_verify_step_checks_without_recording(sandbox):
    r = sandbox.run("verify-step", "03")
    assert r.returncode == 0 and any("HANBIT_RAW.CLAIMS.CLAIMS" in c for c in sandbox.calls())
    assert not (sandbox.repo / ".progress").exists() and "not recorded" in r.stdout

def test_verify_step_execute_records(sandbox):
    sandbox.run("verify-step", "03", "--execute")
    assert '"03"' in (sandbox.repo / ".progress/state.json").read_text()

def test_failed_check_is_not_recorded(sandbox):
    sandbox.fake("snow", "exit 1")
    r = sandbox.run("verify-step", "03", "--execute")
    assert r.returncode != 0 and not (sandbox.repo / ".progress").exists()

def test_verify_step_dry_run_runs_nothing(sandbox):
    assert sandbox.run("verify-step", "03", "--dry-run").returncode == 0 and sandbox.calls() == []
```

- [ ] **手順 2: 実行して失敗を確認する**

実行: `uv run pytest tests/test_script_mixed.py -q`
期待結果: FAIL(teardown はフラグなしで終了コード 1、verify-step はクエリを実行しない)。

- [ ] **手順 3: 実装する**
  - `teardown`: `PREVIEW_HINT="--execute --yes"` を設定する。拒否(終了コード 1)するのは、`DRY_RUN=0` で `--yes` がない場合だけ。`cost-guard` には `--execute` を明示的に渡して呼び出す。最後のメッセージは `done_msg` を使う。
  - `preflight`: 不明な引数は終了コード 64。`PRINT_ONLY=1` では現状の一覧表示のみの分岐を維持する。それ以外では読み取り専用のチェックを実行する。プローブは `DRY_RUN=0` のときだけ実行し、そうでなければ `[dry-run] would run: <probe>` と行 `iceberg-snowflake-storage skip "probe not run; it creates and drops PREFLIGHT_SCRATCH"` を出力する。ツール不足の行は `run scripts/install-tools --execute` と表示する。
  - `verify-step`: `PRINT_ONLY=1` でない限りチェックを実行する(`PRINT_ONLY=1` ならチェック内容を表示する)。`DRY_RUN=1` なら記録の前に終了し、チェックを実行した場合は `step <N> check passed; progress not recorded` をログに出す。
  - 各 `Usage:` コメントを更新する。

- [ ] **手順 4: 確認する**

実行: `uv run pytest -q && find scripts tests -type f \( -perm -u+x -o -name "*.sh" \) | xargs shellcheck`
期待結果: すべて成功、shellcheck の出力なし。

---

### タスク 3: 変更を行うスクリプト

**ファイル:**
- 変更: `scripts/apply-curated`、`apply-policies`、`attach-monitors`、`bootstrap`、`gen-data`、`install-tools`、`load-batch`、`setup-github`、`stream-load`
- 作成: `tests/test_script_mutating.py`

**インターフェース:**
- 利用するもの: タスク 1 のヘルパーと `sandbox`。

- [ ] **手順 1: 失敗するテストを書く**

```python
CASES = {  # script: (args, substring of a call that proves --execute acted)
    "apply-curated": ((), "curated.sql"),
    "apply-policies": ((), "policies_attach.sql"),
    "attach-monitors": ((), "ALTER WAREHOUSE"),
    "bootstrap": ((), "CREATE RESOURCE MONITOR"),
    "gen-data": (("--rows", "10"), "hanbit_gen.cli --rows 10"),
    "install-tools": ((), "uv tool install snowflake-cli"),
    "load-batch": ((), "COPY INTO"),
    "setup-github": (("--skip-secrets",), "gh api -X PUT"),
    "stream-load": (("--domain", "claims"), "sfops.streaming"),
}
READ_ONLY_GH = ("gh auth status", "gh repo view", "gh api user")

def prepare(sandbox, script):
    if script == "install-tools":
        sandbox.unfake("snow")
    if script == "bootstrap":  # existing key files: --execute needs no real openssl
        (sandbox.home / ".snowflake").mkdir()
        for name in ("handson_tf_key.p8", "handson_tf_key.pub"):
            (sandbox.home / ".snowflake" / name).write_text("x\n")
        (sandbox.home / ".snowflake/connections.toml").write_text("[handson_tf]\n")

@pytest.mark.parametrize("script", CASES)
@pytest.mark.parametrize("flags", [(), ("--dry-run",)])
def test_preview_changes_nothing(sandbox, script, flags):
    prepare(sandbox, script)
    before = sandbox.snapshot()
    r = sandbox.run(script, *CASES[script][0], *flags)
    assert r.returncode == 0, r.stderr
    assert [c for c in sandbox.calls() if not c.startswith(READ_ONLY_GH)] == []
    assert sandbox.snapshot() == before
    assert r.stdout.rstrip().endswith("[preview] nothing was changed. Re-run with --execute to apply.")
    for claim in ("done.", " ready", "generating", "added [", "branch protection on main:"):
        assert claim not in r.stdout

@pytest.mark.parametrize("script", CASES)
def test_execute_acts(sandbox, script):
    prepare(sandbox, script)
    args, proof = CASES[script]
    r = sandbox.run(script, *args, "--execute", env={"PRIVATE_KEY_PASSPHRASE": "x"})
    assert r.returncode == 0, r.stderr
    assert any(proof in c for c in sandbox.calls())
    assert "[preview]" not in r.stdout

def test_fresh_bootstrap_preview_creates_no_files(sandbox):
    assert sandbox.run("bootstrap").returncode == 0
    assert not (sandbox.home / ".snowflake").exists()

def test_setup_github_preview_with_every_option_only_reads(sandbox):
    r = sandbox.run("setup-github", "--branch-protection", env={"TF_API_TOKEN": "not-a-token"})
    assert all(c.startswith(READ_ONLY_GH) for c in sandbox.calls())  # also matches "gh api users/me"
    assert "not-a-token" not in r.stdout

def test_install_tools_rejects_typo(sandbox):
    assert sandbox.run("install-tools", "--exceute").returncode == 64 and sandbox.calls() == []
```

- [ ] **手順 2: 実行して失敗を確認する**

実行: `uv run pytest tests/test_script_mutating.py -q`
期待結果: FAIL(`gen-data` がプレビューで `uv` を呼び出す、成功メッセージが表示される)。

- [ ] **手順 3: 実装する**
  - 共通: 作業終了や成功を伝えるメッセージは、すべて `done_msg` を通す。メッセージ内の「次の手順」のコマンドは、何かを変更する場合は `--execute` を付ける。`Usage:` コメントを更新する。
  - `gen-data`: `common.sh` を source し、`parse_common_flags` の後、`REST_ARGS` を付けて `run uv run python -m hanbit_gen.cli` を実行する(プレビュー行を出力できるように、`exec` は使わない)。
  - `install-tools`: 残った引数があれば終了コード 64。
  - `bootstrap`: "generating..." は実行時にだけログに出す。プレビューでは、`[handson_tf]` がない場合に `connections.toml` へ追記することも表示する。
  - `setup-github`: `environment <name> ready`、ブランチ保護の行、最後の行は `done_msg` を使う。
  - `load-batch`: エラーメッセージは `run scripts/gen-data --execute first` とする。

- [ ] **手順 4: 確認する**

実行: `uv run pytest -q && find scripts tests -type f \( -perm -u+x -o -name "*.sh" \) | xargs shellcheck`
期待結果: すべて成功、shellcheck の出力なし。

---

### タスク 4: `sync_doc_nav.py`

**ファイル:**
- 変更: `scripts/sync_doc_nav.py`
- 変更: `tests/test_docs_nav.py`

**インターフェース:**
- 提供するもの: `main(argv: list[str] | None = None) -> int`。フラグなし、または `--dry-run`: 古いファイルごとに `would update: <path>` を出力し、続けてプレビュー行を出力して終了コード 0。`--execute`: 書き込んで `updated: <path>` を出力する。`--check`: 変更なし。`--check --execute`、`--dry-run --execute`、不明な引数: 終了コード 64。

- [ ] **手順 1: 失敗するテストを書く。** ヘルパーは、スクリプトを `tmp_path/scripts/` にコピーし、`ORDER` のすべてのガイドを両言語で `# T\n` だけの内容で作成します

```python
@pytest.mark.parametrize("flags", [[], ["--dry-run"]])
def test_nav_preview_writes_nothing(tmp_path, flags):
    script, guide = make_tree(tmp_path)
    r = run_nav(script, *flags)
    assert r.returncode == 0 and "would update:" in r.stdout
    assert "nothing was changed" in r.stdout and guide.read_text() == "# T\n"

def test_nav_execute_writes(tmp_path):
    script, guide = make_tree(tmp_path)
    assert run_nav(script, "--execute").returncode == 0
    assert "<!-- nav:top -->" in guide.read_text()

@pytest.mark.parametrize("flags", [["--check", "--execute"], ["--dry-run", "--execute"], ["--exceute"]])
def test_nav_rejects_bad_flags(tmp_path, flags):
    script, guide = make_tree(tmp_path)
    assert run_nav(script, *flags).returncode == 64 and guide.read_text() == "# T\n"
```

- [ ] **手順 2:** `uv run pytest tests/test_docs_nav.py -q` を実行する。期待結果: FAIL(プレビューが書き込んでしまう)。
- [ ] **手順 3:** インターフェースどおりに `main` を実装し、モジュールの docstring を更新する。
- [ ] **手順 4:** `uv run pytest tests/test_docs_nav.py -q && uv run ruff check` を実行する。期待結果: 成功。

---

### タスク 5: Python のメッセージと生成ファイルのヘッダー

**ファイル:**
- 変更: `src/sfops/cost.py:51`、`src/sfops/conn.py:27,31`、`src/hanbit_gen/ddl.py:8`、`src/hanbit_gen/curated.py:8`(同ファイル内の他のヘッダーがあればそれも)、`sql/policies_attach.sql` のコメント
- 再生成: `sql/raw_tables.sql`、`sql/curated.sql`
- テスト: `tests/test_cost.py`

- [ ] **手順 1: 失敗するテストを追加する**(モジュールの既存の import に `CostRow`、`format_report` を加えて使う)

```python
def test_stop_report_gives_a_command_that_really_suspends():
    assert "scripts/cost-guard --suspend-all --execute" in format_report([CostRow("X", 81.0)])
```

- [ ] **手順 2:** `uv run pytest tests/test_cost.py -q` を実行する。期待結果: FAIL。
- [ ] **手順 3:** 「これを実行」の各コマンドに `--execute` を追加する: `cost-guard --suspend-all`、`bootstrap`、`gen-data --emit-*`、`apply-policies`。読み取り専用スクリプトへの説明的な言及はそのままにする。
- [ ] **手順 4:** 再生成する: `scripts/gen-data --execute --emit-ddl sql/raw_tables.sql` と `scripts/gen-data --execute --emit-curated sql/curated.sql`
- [ ] **手順 5:** `uv run pytest -q && git diff --stat sql/` を実行する。期待結果: 成功し、`sql/` の差分はコメント行のみ。

---

### タスク 6: ドキュメント、Claude のコマンドとスキル

**ファイル:**
- 変更: `docs/guides/*.md`、`docs/ja/guides/*.md`、`README.md`、`README.ja.md`、`CONTRIBUTING.md`、`CLAUDE.md`、`SECURITY.md`(言及の修正が必要な場合のみ)、`.claude/commands/*.md`、`.claude/skills/*/SKILL.md`
- 作成: `tests/test_docs_commands.py`

- [ ] **手順 1: 失敗するテストを書く。** `code_blocks(path) -> list[list[str]]` は、フェンスで囲まれたブロックごとに、(前後の空白を除いた後で)`scripts/` で始まる行を、` #` 以降のコメントを取り除いて返します。

```python
CHANGES = ("apply-curated", "apply-policies", "attach-monitors", "bootstrap", "gen-data", "install-tools",
           "load-batch", "setup-github", "stream-load", "teardown", "verify-step", "cost-guard --suspend-all")

def test_each_block_that_shows_a_changing_script_shows_how_to_execute_it():
    missing = []
    for f in [*EN_GUIDES, *JA_GUIDES]:
        for block in code_blocks(f):
            for name in CHANGES:
                lines = [c for c in block if re.match(rf"scripts/{re.escape(name)}(\s|$)", c)]
                if lines and not any("--execute" in c.split() for c in lines):
                    missing.append(f"{f.relative_to(ROOT)}: {name}")
    assert not missing, missing

@pytest.mark.parametrize("en", EN_GUIDES, ids=lambda p: p.stem)
def test_japanese_guides_run_the_same_commands(en):
    assert code_blocks(en) == code_blocks(ROOT / "docs/ja/guides" / en.name)
```

- [ ] **手順 2:** `uv run pytest tests/test_docs_commands.py -q` を実行する。期待結果: 1 つ目のテストが FAIL。一致テストが既存の差異で失敗する場合は、同じ編集でずれを直す。

- [ ] **手順 3: 両言語のドキュメントを編集する**
  - プレビューの行は `--dry-run` を外し(コマンドのみ)、実行の行には `--execute` を付ける。対象は `install-tools`、`bootstrap`、`load-batch`、`apply-curated`、`setup-github`、`teardown`(`--execute --yes`)。
  - プレビュー行のない実行の行と、変更を行うスクリプトの実行や再実行を読者に指示する本文に、`--execute` を追加する。説明的な言及(「`scripts/bootstrap` が作成する」など)はそのままにする。
  - ガイド 01: まず `scripts/preflight`(読み取り専用)、次に Iceberg のプローブ用の `scripts/preflight --execute`。確認ブロックは `scripts/preflight` のままにする。
  - `verify-step N` は `verify-step N --execute` にする。ガイド 00 で、これがないとチェックは実行されるが記録されないことを説明する。
  - ガイド 00 に、ルールを説明する短い段落を 1 つ追加する: 既定はプレビュー、実行には `--execute`、読み取り専用のチェックはフラグ不要。
  - `access-matrix --dry-run`(「解析のみ」)はそのままにする。
  - `CONTRIBUTING.md` と `CLAUDE.md`: スクリプトの新ルール、`sync_doc_nav.py --execute`。
  - `.claude`: `sf-teardown` は `scripts/teardown` でプレビューし、明示的な確認を得た後にだけ `--execute --yes` を実行する。`sf-verify` とガイドのスキルは、記録に `--execute` を使う。`sf-cost` と cost-watch スキルは `cost-guard --suspend-all --execute` を勧め、先に確認を取る。`sf-preflight` はフラグなしのままにする。

- [ ] **手順 4: すべてを確認する**

実行:
```bash
uv run pytest --cov --cov-fail-under=80 && uv run ruff check && uv run ty check src
find scripts tests -type f \( -perm -u+x -o -name "*.sh" \) | xargs shellcheck
scripts/check-secrets
grep -rnE -e '--dry-run|teardown --yes' README*.md CONTRIBUTING.md CLAUDE.md docs/guides docs/ja .claude src scripts
```
期待結果: テスト、lint、型チェック、shellcheck が成功し、`[check-secrets] clean` となること。grep の一致は、すべて意図した `--dry-run` 対応の行か `access-matrix --dry-run` であること。

- [ ] **手順 5: 実際のプレビューを実行する**(`--execute` を付けないので安全): `scripts/bootstrap`、`scripts/teardown`、`scripts/cost-guard --suspend-all`、`scripts/gen-data`。期待結果: それぞれがプレビュー行で終わり、`git status --short` が変化しないこと。
