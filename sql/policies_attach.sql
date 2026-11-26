-- Run by scripts/apply-policies --execute as the TERRAFORM identity (role TF_ADMIN). Idempotent.
-- Row-access entitlements are DATA: change who sees which region by editing rows, not policy code.
CREATE TABLE IF NOT EXISTS HANBIT_GOV.ENTITLEMENTS.ROLE_REGION (ROLE_NAME VARCHAR, REGION VARCHAR);
DELETE FROM HANBIT_GOV.ENTITLEMENTS.ROLE_REGION;
INSERT INTO HANBIT_GOV.ENTITLEMENTS.ROLE_REGION VALUES
  ('CLAIMS_ADJUSTER', 'Seoul'),
  ('LOAN_OFFICER', 'Busan'),
  ('UNDERWRITER', '*'),
  ('FRAUD_ANALYST', '*'),
  ('FINANCE_CONTROLLER', '*'),
  ('MARKETING_ANALYST', '*');

-- No Terraform resource exists for aggregation policies (provider 2.23.0), so it lives here.
CREATE AGGREGATION POLICY IF NOT EXISTS HANBIT_GOV.POLICIES.AGG_MIN_GROUP_5
  AS () RETURNS AGGREGATION_CONSTRAINT ->
  CASE WHEN IS_ROLE_IN_SESSION('MARKETING_ANALYST')
       THEN AGGREGATION_CONSTRAINT(MIN_GROUP_SIZE => 5)
       ELSE NO_AGGREGATION_CONSTRAINT() END;

-- Service identity: key-pair only. Done in SQL because the Terraform attachment resource cannot read the reference back
-- as TF_ADMIN (provider 2.23.0). TF_ADMIN has APPLY AUTHENTICATION POLICY on this user (scripts/bootstrap).
-- FORCE makes it idempotent: without it, a re-run (or a policy the earlier Terraform attachment already set) fails with
-- "Object TERRAFORM already has a AUTHENTICATION_POLICY".
ALTER USER TERRAFORM SET AUTHENTICATION POLICY HANBIT_GOV.POLICIES.AP_SERVICE FORCE;
