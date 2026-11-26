# 06 · BI and AI

<!-- nav:top -->
[🏠 7-day map](../../README.md#7-day-map) · ← [04 Governance](04-governance.md) · [07 Monitoring & FinOps](07-monitoring-finops-teardown.md) →
<!-- /nav:top -->

**Japanese version:** [../ja/guides/06-bi-and-ai.md](../ja/guides/06-bi-and-ai.md)

## 1. BI: a Streamlit dashboard inside Snowflake
`apps/streamlit/` is a small dashboard (claims by region, plus platform credits). It runs inside Snowflake, so data never leaves the account and the role's masking and row policies still apply. Deploy it under a least-privilege role, not an admin role:
```bash
snow sql -c handson_tf -f sql/streamlit.sql   # creates the stage, grants and the app
snow sql -c handson_tf -q "PUT file://apps/streamlit/* @HANBIT_MARTS.APPS.STREAMLIT_STAGE/claims AUTO_COMPRESS=FALSE OVERWRITE=TRUE"   # uploads the app files
```
Open it in Snowsight (Projects > Streamlit) as `CLAIMS_ADJUSTER`: only Seoul rows appear. Switch role to see a different view. The status filter is allow-listed in `queries.py` (unit-tested), never string-interpolated from user input.

## 2. AI: Cortex / Cortex Code (only if available in Seoul)
`scripts/preflight` reports whether Cortex is available in ap-northeast-2 and whether cross-region inference is needed. **Rule for this repo: stay in-region.** If Cortex needs cross-region inference, skip this section.

If available:
1. **Set the spend cap first**: `ALTER ACCOUNT SET CORTEX_CODE_CLI_DAILY_EST_CREDIT_LIMIT_PER_USER = <small number>;` (preflight prints the current value). AI features meter per token and can surprise you.
2. Create the semantic view `sql/semantic_view.sql`. It deliberately exposes only non-sensitive columns, so natural-language questions cannot reach HEALTH data.
3. Ask Cortex Analyst: "total claim amount by region last quarter". Compare its generated SQL with the dashboard query.
4. **Governance check:** ask as `MARKETING_ANALYST` for diagnosis codes. The answer must be refused or masked: AI inherits Snowflake's controls only because the data policies live on the columns, not in the app.

## Cost of this step
Dashboard: about 2 credits (BI_WH, auto-suspend 60 s). AI: budget up to 5 credits, capped by the setting above; 0 if skipped.

## Verify

```bash
snow sql -c handson_tf -q "SHOW STREAMLITS IN SCHEMA HANBIT_MARTS.APPS"          # CLAIMS_DASH
snow sql -c handson_tf -q "LIST @HANBIT_MARTS.APPS.STREAMLIT_STAGE/claims"       # app.py and the other uploaded files
scripts/verify-step 06 --execute
```
Then open **Projects > Streamlit > CLAIMS_DASH** in Snowsight. Expect regions for `CLAIMS_ADJUSTER` only. If AI is enabled, the sensitive-column question is refused or masked.

---
<!-- nav:bottom -->
[🏠 7-day map](../../README.md#7-day-map) · ← [04 Governance](04-governance.md) · [07 Monitoring & FinOps](07-monitoring-finops-teardown.md) →
<!-- /nav:bottom -->
