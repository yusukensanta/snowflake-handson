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
