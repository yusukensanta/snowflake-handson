-- Iceberg v3 table on Snowflake-managed storage (no customer AWS account needed).
-- UNVERIFIED LIVE: the exact clause for Snowflake-managed storage (GA 2026-06-01) and Seoul availability
-- are checked by scripts/preflight. If CREATE fails, see guide 05 "Fallback". Run as TF_ADMIN/PLATFORM role.
-- Docs: CREATE ICEBERG TABLE (Snowflake as the Iceberg catalog); ICEBERG_VERSION is fixed at creation.
USE ROLE TF_ADMIN;
USE WAREHOUSE TRANSFORM_WH;
CREATE SCHEMA IF NOT EXISTS HANBIT_MARTS.LAKE;

-- Non-sensitive, pseudonymised claims facts only: external engines bypass Snowflake roles unless
-- they go through the Horizon catalog, so never put raw PII in an open-format table.
CREATE ICEBERG TABLE IF NOT EXISTS HANBIT_MARTS.LAKE.CLAIMS_FACT
  CATALOG = 'SNOWFLAKE'
  EXTERNAL_VOLUME = 'SNOWFLAKE_MANAGED'
  ICEBERG_VERSION = 3
  AS
SELECT CLAIM_ID, CUSTOMER_PSEUDO_ID, REGION, CLAIM_AMOUNT, STATUS, FILED_DATE
FROM HANBIT_CURATED.CLAIMS.CLAIMS;

SHOW PARAMETERS LIKE 'ICEBERG_VERSION' IN TABLE HANBIT_MARTS.LAKE.CLAIMS_FACT;
SELECT COUNT(*) FROM HANBIT_MARTS.LAKE.CLAIMS_FACT;
