-- Deploy the dashboard. Streamlit apps run with OWNER rights in many setups, so deploy under a
-- role that only has the access the dashboard should show (CLAIMS_ADJUSTER here), not TF_ADMIN.
-- UNVERIFIED LIVE: stage/app syntax; run once, check the app opens in Snowsight > Projects > Streamlit.
USE ROLE TF_ADMIN;
CREATE SCHEMA IF NOT EXISTS HANBIT_MARTS.APPS;
CREATE STAGE IF NOT EXISTS HANBIT_MARTS.APPS.STREAMLIT_STAGE DIRECTORY = (ENABLE = TRUE);
GRANT USAGE, CREATE STREAMLIT ON SCHEMA HANBIT_MARTS.APPS TO ROLE CLAIMS_ADJUSTER;
GRANT READ, WRITE ON STAGE HANBIT_MARTS.APPS.STREAMLIT_STAGE TO ROLE CLAIMS_ADJUSTER;
USE ROLE CLAIMS_ADJUSTER;  -- the app owner: the app can show only what this role may see
-- PUT files: snow sql -q "PUT file://apps/streamlit/* @HANBIT_MARTS.APPS.STREAMLIT_STAGE/claims AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
CREATE STREAMLIT IF NOT EXISTS HANBIT_MARTS.APPS.CLAIMS_DASH
  ROOT_LOCATION = '@HANBIT_MARTS.APPS.STREAMLIT_STAGE/claims'
  MAIN_FILE = 'app.py'
  QUERY_WAREHOUSE = BI_WH;
