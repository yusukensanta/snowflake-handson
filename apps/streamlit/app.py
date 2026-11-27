"""Hanbit claims dashboard (Streamlit in Snowflake). Owner's rights: every viewer sees what the app's owner role
(CLAIMS_ADJUSTER) may see, whatever role the viewer uses."""
import streamlit as st
from queries import ALLOWED_STATUS, claims_by_region_sql
from snowflake.snowpark.context import get_active_session

session = get_active_session()
st.title("Hanbit claims overview")
status = st.selectbox("Status", [None, *sorted(ALLOWED_STATUS)])
df = session.sql(claims_by_region_sql(status)).to_pandas()
st.bar_chart(df, x="REGION", y="TOTAL_AMOUNT")
st.dataframe(df)
