# 06 · BI and AI

<!-- nav:top -->
[🏠 7-day map](../../README.md#7-day-map) · ← [04 Governance](04-governance.md) · [07 Monitoring & FinOps](07-monitoring-finops-teardown.md) →
<!-- /nav:top -->

**Japanese version:** [../ja/guides/06-bi-and-ai.md](../ja/guides/06-bi-and-ai.md)

## 1. BI: a Streamlit dashboard inside Snowflake
`apps/streamlit/` is a small dashboard of claims by region. It runs inside Snowflake, so data never leaves the account. Streamlit apps run with **owner's rights**: queries use the privileges and policies of the role that owns the app, not the viewer's. Choosing the owner is therefore the security decision, so the app is owned by the persona that needs this data (`CLAIMS_ADJUSTER`), never an admin role.

**Prerequisite:** guide 04 is done, with `grant_personas_to_user` set to the user of your `handson_admin` connection and applied (guide 02). Run from the repo root with `PRIVATE_KEY_PASSPHRASE` exported.

```bash
snow sql -c handson_tf -f sql/streamlit.sql          # 1. as TF_ADMIN: schema, stage, grants
snow sql -c handson_admin -f sql/streamlit_app.sql   # 2. as CLAIMS_ADJUSTER: upload the files, create the app
```
- Two connections, because only step 2 needs a role that can read claims, and the Terraform service user never gets one.
- Step 2 copies the files into the app when it creates it. Re-run it after editing the app (this drops any `USAGE` grants made on the app).

Open **Projects > Streamlit > CLAIMS_DASH** in Snowsight as `CLAIMS_ADJUSTER`: only Seoul rows appear. Other personas cannot open the app, and granting them access would show them the same Seoul rows, not their own view. The status filter is allow-listed in `queries.py` (unit-tested), never string-interpolated from user input. Platform credits are not on this dashboard because claims staff do not need cost data; use `scripts/cost-report` (guide 07).

## 2. AI: Cortex Analyst (skip it in Seoul)
As of 2026-11-27, the [Cortex Analyst documentation](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst) does not list AWS ap-northeast-2 (Seoul) as a native region, so there it needs cross-region inference. **Rule for this repo: stay in-region.** With an account in Seoul, skip this section. `scripts/preflight` prints `CORTEX_ENABLED_CROSS_REGION`; it does not check availability and never changes the setting.

If your region is listed (these steps have not been run against a live account):
1. **Know the cost controls first.** Analyst is billed per message, plus warehouse time for the SQL it generates. Usage is in the `CORTEX_ANALYST_USAGE_HISTORY` view, and `ALTER ACCOUNT SET ENABLE_CORTEX_ANALYST = FALSE;` (ACCOUNTADMIN) switches it off afterwards. `CORTEX_CODE_CLI_DAILY_EST_CREDIT_LIMIT_PER_USER` caps only the Cortex Code CLI, not Analyst.
2. Create the semantic view `sql/semantic_view.sql`. It exposes only non-sensitive columns. The file grants nothing: the asking role needs the `SNOWFLAKE.CORTEX_USER` or `SNOWFLAKE.CORTEX_ANALYST_USER` database role and `SELECT` on the table behind the view.
3. Ask Cortex Analyst: "total claim amount by region last quarter". Compare its generated SQL with the dashboard query.
4. **Governance check:** ask for diagnosis codes. The semantic view leaves that column out, so there is nothing to answer from. `MARKETING_ANALYST` has no `SELECT` on the claims table at all. These checks show the view's scope and the grants at work, not masking; the access matrix (guide 04) is what proves masking.

## Cost of this step
Dashboard: about 2 credits (BI_WH, auto-suspend 60 s). AI: 0 if skipped; otherwise a few questions, billed per message.

## Verify

```bash
snow sql -c handson_admin --role CLAIMS_ADJUSTER -q "SHOW STREAMLITS IN SCHEMA HANBIT_MARTS.APPS"   # CLAIMS_DASH
snow sql -c handson_tf -q "LIST @HANBIT_MARTS.APPS.STREAMLIT_STAGE/claims"                          # app.py, queries.py, environment.yml
scripts/verify-step 06 --execute
```
`verify-step` only checks that its query runs, so confirm `CLAIMS_DASH` in the first output yourself. Then open the app as above and expect Seoul rows only.

---
<!-- nav:bottom -->
[🏠 7-day map](../../README.md#7-day-map) · ← [04 Governance](04-governance.md) · [07 Monitoring & FinOps](07-monitoring-finops-teardown.md) →
<!-- /nav:bottom -->
