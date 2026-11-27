-- Dashboard setup, step 1 of 2: schema, stage and grants. Run over handson_tf (TF_ADMIN):
--   snow sql -c handson_tf -f sql/streamlit.sql
-- The app itself is created by sql/streamlit_app.sql under the role that owns it, so that the Terraform
-- service identity never needs a role that can read claims data. Safe to re-run.
USE ROLE TF_ADMIN;
CREATE SCHEMA IF NOT EXISTS HANBIT_MARTS.APPS;
CREATE STAGE IF NOT EXISTS HANBIT_MARTS.APPS.STREAMLIT_STAGE DIRECTORY = (ENABLE = TRUE);
GRANT USAGE, CREATE STREAMLIT ON SCHEMA HANBIT_MARTS.APPS TO ROLE CLAIMS_ADJUSTER;
GRANT READ, WRITE ON STAGE HANBIT_MARTS.APPS.STREAMLIT_STAGE TO ROLE CLAIMS_ADJUSTER;
