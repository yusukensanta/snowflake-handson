"""Hanbit claims dashboard (Streamlit in Snowflake). Runs as the viewing role's owner-rights app:
masking/row policies of the app's role apply, so every viewer persona sees only what that role may."""
import streamlit as st
from queries import ALLOWED_STATUS, claims_by_region_sql, credits_sql
from snowflake.snowpark.context import get_active_session

session = get_active_session()
st.title("Hanbit claims overview")
status = st.selectbox("Status", [None, *sorted(ALLOWED_STATUS)])
df = session.sql(claims_by_region_sql(status)).to_pandas()
st.bar_chart(df, x="REGION", y="TOTAL_AMOUNT")
st.dataframe(df)
with st.expander("Platform credits (last 14 days)"):
    st.line_chart(session.sql(credits_sql()).to_pandas(), x="DAY", y="CREDITS", color="WAREHOUSE_NAME")
