"""The dashboard deploys in two steps with two identities: setup (TF_ADMIN) and app (the owner role)."""
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
APP_DIR = ROOT / "apps/streamlit"
STAGE_PATH = "@HANBIT_MARTS.APPS.STREAMLIT_STAGE/claims"


def statements(name: str) -> list[str]:
    """SQL statements of a file in sql/, without comments, whitespace collapsed."""
    code = "\n".join(line.split("--")[0] for line in (ROOT / "sql" / name).read_text().splitlines())
    return [" ".join(s.split()) for s in code.split(";") if s.strip()]


def index_of(stmts: list[str], prefix: str) -> int:
    return next(i for i, s in enumerate(stmts) if s.startswith(prefix))


def test_setup_only_uses_tf_admin_and_creates_no_app():
    stmts = statements("streamlit.sql")
    assert [s for s in stmts if s.startswith("USE ")] == ["USE ROLE TF_ADMIN"]
    assert not any(re.match(r"CREATE( OR REPLACE)? STREAMLIT", s) for s in stmts)


def test_setup_grants_what_the_owner_role_needs():
    stmts = statements("streamlit.sql")
    assert "GRANT USAGE, CREATE STREAMLIT ON SCHEMA HANBIT_MARTS.APPS TO ROLE CLAIMS_ADJUSTER" in stmts
    assert "GRANT READ, WRITE ON STAGE HANBIT_MARTS.APPS.STREAMLIT_STAGE TO ROLE CLAIMS_ADJUSTER" in stmts


def test_app_is_deployed_as_the_owner_role():
    stmts = statements("streamlit_app.sql")
    assert [s for s in stmts if s.startswith("USE ")] == ["USE ROLE CLAIMS_ADJUSTER"]
    assert stmts[0] == "USE ROLE CLAIMS_ADJUSTER"


def test_upload_names_every_app_file_and_nothing_else():
    puts = [s for s in statements("streamlit_app.sql") if s.startswith("PUT ")]
    uploaded = sorted(s.split()[1] for s in puts)
    expected = sorted(f"file://apps/streamlit/{p.name}" for p in APP_DIR.iterdir() if p.is_file())
    assert uploaded == expected  # no wildcard: it would also match __pycache__ and PUT rejects directories
    assert all(s.split()[2] == STAGE_PATH for s in puts)
    assert all("AUTO_COMPRESS=FALSE" in s and "OVERWRITE=TRUE" in s for s in puts)


def test_app_is_created_from_the_uploaded_files_then_made_live():
    stmts = statements("streamlit_app.sql")
    create = index_of(stmts, "CREATE OR REPLACE STREAMLIT HANBIT_MARTS.APPS.CLAIMS_DASH")
    last_put = max(i for i, s in enumerate(stmts) if s.startswith("PUT "))
    live = index_of(stmts, "ALTER STREAMLIT HANBIT_MARTS.APPS.CLAIMS_DASH ADD LIVE VERSION FROM LAST")
    assert last_put < create < live  # FROM copies the files once, at CREATE time
    assert f"FROM '{STAGE_PATH}'" in stmts[create]
    assert "ROOT_LOCATION" not in stmts[create]
    assert "MAIN_FILE = 'app.py'" in stmts[create] and "QUERY_WAREHOUSE = BI_WH" in stmts[create]


def test_dashboard_reads_only_what_the_owner_role_is_granted():
    source = "".join(p.read_text() for p in APP_DIR.glob("*.py"))
    assert set(re.findall(r"HANBIT_\w+\.\w+", source)) == {"HANBIT_CURATED.CLAIMS"}
