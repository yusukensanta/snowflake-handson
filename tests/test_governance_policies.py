"""Policy bodies that Snowflake accepts at CREATE time but rejects when a query uses them."""
import re
from pathlib import Path

TF = (Path(__file__).parents[1] / "terraform/modules/governance/main.tf").read_text()
BODY = re.search(r'resource "snowflake_projection_policy" "id_joinable" \{.*?body\s*=\s*"([^"]*)"', TF, re.DOTALL)


def test_projection_constraint_takes_only_literal_booleans():
    assert BODY
    arguments = re.findall(r"PROJECTION_CONSTRAINT\(ALLOW => (.*?)\)(?= ELSE| END|$)", BODY[1])
    assert arguments and set(arguments) <= {"true", "false"}, arguments


def test_projection_is_denied_to_marketing_and_allowed_to_everyone_else():
    assert BODY
    assert BODY[1] == (
        "CASE WHEN IS_ROLE_IN_SESSION('MARKETING_ANALYST') THEN PROJECTION_CONSTRAINT(ALLOW => false) "
        "ELSE PROJECTION_CONSTRAINT(ALLOW => true) END"
    )


TAG = re.search(r'resource "snowflake_tag" "sensitivity" \{.*?\n\}', TF, re.DOTALL)


def test_tag_resource_manages_its_masking_policies_so_a_plan_detects_detachment():
    assert TAG
    for policy in ("sensitive_string", "sensitive_number"):
        assert f"snowflake_masking_policy.{policy}.fully_qualified_name" in TAG[0]
    assert "ignore_changes" not in TAG[0]


def test_nothing_attaches_masking_outside_drift_detection():
    assert 'resource "snowflake_execute" "tag_masking"' not in TF
    # forget the old resource without running its revert, which would UNSET the policies
    assert re.search(
        r"removed \{\s*from = snowflake_execute\.tag_masking\s*lifecycle \{\s*destroy = false\s*\}\s*\}", TF
    )
