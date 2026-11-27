-- Dashboard setup, step 2 of 2: upload the files and create the app as its owner. Run from the repo root over a
-- connection whose user holds CLAIMS_ADJUSTER (grant_personas_to_user, guide 02):
--   snow sql -c handson_admin -f sql/streamlit_app.sql
-- Streamlit apps run with OWNER's rights: every viewer sees what CLAIMS_ADJUSTER may see. Choose the owner role
-- with that in mind. Safe to re-run: it redeploys the app, which drops any USAGE grants made on it.
-- UNVERIFIED LIVE: run once, then check the app opens in Snowsight > Projects > Streamlit.
USE ROLE CLAIMS_ADJUSTER;
-- One PUT per file: a wildcard would also match __pycache__, and PUT rejects directories.
PUT file://apps/streamlit/app.py @HANBIT_MARTS.APPS.STREAMLIT_STAGE/claims AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://apps/streamlit/queries.py @HANBIT_MARTS.APPS.STREAMLIT_STAGE/claims AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://apps/streamlit/environment.yml @HANBIT_MARTS.APPS.STREAMLIT_STAGE/claims AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
-- FROM copies the files at CREATE time only, so upload first and re-run this file after editing the app.
CREATE OR REPLACE STREAMLIT HANBIT_MARTS.APPS.CLAIMS_DASH
  FROM '@HANBIT_MARTS.APPS.STREAMLIT_STAGE/claims'
  MAIN_FILE = 'app.py'
  QUERY_WAREHOUSE = BI_WH;
ALTER STREAMLIT HANBIT_MARTS.APPS.CLAIMS_DASH ADD LIVE VERSION FROM LAST;
