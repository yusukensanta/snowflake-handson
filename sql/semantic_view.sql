-- Semantic view for Cortex Analyst (natural-language questions). Only if Cortex is available in your region
-- (scripts/preflight reports it). UNVERIFIED LIVE: check CREATE SEMANTIC VIEW syntax in current docs first.
USE ROLE TF_ADMIN;
CREATE OR REPLACE SEMANTIC VIEW HANBIT_MARTS.APPS.CLAIMS_SV
  TABLES (claims AS HANBIT_CURATED.CLAIMS.CLAIMS PRIMARY KEY (CLAIM_ID))
  DIMENSIONS (claims.region AS REGION, claims.status AS STATUS, claims.filed_date AS FILED_DATE)
  METRICS (claims.total_amount AS SUM(CLAIM_AMOUNT), claims.claim_count AS COUNT(CLAIM_ID))
  COMMENT = 'Claims facts; sensitive columns intentionally excluded';
