"""SQL builders for the dashboard. Pure functions so they are unit-testable."""
ALLOWED_STATUS = {"filed", "review", "paid", "denied"}
TABLE = "HANBIT_CURATED.CLAIMS.CLAIMS"


def claims_by_region_sql(status: str | None = None) -> str:
    where = f" WHERE status = '{status}'" if status in ALLOWED_STATUS else ""
    return (f"SELECT REGION, COUNT(*) AS CLAIMS, SUM(CLAIM_AMOUNT) AS TOTAL_AMOUNT "
            f"FROM {TABLE}{where} GROUP BY REGION ORDER BY TOTAL_AMOUNT DESC")


def credits_sql() -> str:
    return ("SELECT DAY, WAREHOUSE_NAME, CREDITS FROM HANBIT_OPS.MONITORING.V_CREDITS_BY_WAREHOUSE "
            "WHERE DAY >= DATEADD('day', -14, CURRENT_DATE()) ORDER BY DAY")
