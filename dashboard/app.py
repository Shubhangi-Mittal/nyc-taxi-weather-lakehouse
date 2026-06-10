import pandas as pd
import plotly.express as px
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account

PROJECT = "nyc-lakehouse"
DATASET = "lakehouse"

st.set_page_config(page_title="NYC Taxi & Weather Lakehouse", layout="wide")


@st.cache_resource
def get_client() -> bigquery.Client:
    # On Streamlit Cloud: service account from secrets. Locally: gcloud ADC.
    try:
        sa_info = dict(st.secrets["gcp_service_account"])
    except Exception:
        sa_info = None
    if sa_info:
        creds = service_account.Credentials.from_service_account_info(sa_info)
        return bigquery.Client(credentials=creds, project=PROJECT)
    return bigquery.Client(project=PROJECT)


@st.cache_data(ttl=600)
def load(table: str) -> pd.DataFrame:
    client = get_client()
    return client.query(f"SELECT * FROM `{PROJECT}.{DATASET}.{table}`").to_dataframe()


weather = load("gold_weather_impact")
borough = load("gold_borough_demand")
monthly = load("gold_monthly_volume").sort_values("pickup_month")

st.title("NYC Taxi & Weather Lakehouse")
st.caption(
    "Yellow-taxi trips joined to hourly NYC weather · full-year 2024 · ~40M trips · "
    "dual-cloud (Iceberg + BigQuery)"
)

total_trips = int(weather["trips"].sum())
avg_fare = (weather["avg_fare_usd"] * weather["trips"]).sum() / total_trips
avg_tip = (weather["avg_tip_pct_card"] * weather["trips"]).sum() / total_trips

c1, c2, c3 = st.columns(3)
c1.metric("Total trips (2024)", f"{total_trips:,}")
c2.metric("Avg fare", f"${avg_fare:.2f}")
c3.metric("Card tip %", f"{avg_tip:.1f}%")

st.info(
    "**Key finding:** tipping holds near 25% in clear, rain, and snow alike. "
    "A single month suggested riders tip ~3 points more in the rain — but across a "
    "full year that effect vanished. It was noise, not behavior."
)

left, right = st.columns(2)
with left:
    st.subheader("Tip % by weather")
    fig = px.bar(weather, x="weather_condition", y="avg_tip_pct_card",
                 color="weather_condition", text="avg_tip_pct_card")
    fig.update_yaxes(range=[0, 35], title="Avg card tip %")
    fig.update_xaxes(title="")
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.subheader("Trips by weather")
    fig = px.bar(weather, x="weather_condition", y="trips", color="weather_condition")
    fig.update_xaxes(title="")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Monthly trip volume")
fig = px.line(monthly, x="pickup_month", y="trips", markers=True)
fig.update_yaxes(title="Trips")
fig.update_xaxes(title="Month")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Pickups by borough")
fig = px.bar(borough.sort_values("trips"), x="trips", y="pickup_borough",
             orientation="h")
fig.update_yaxes(title="")
st.plotly_chart(fig, use_container_width=True)
st.dataframe(borough, use_container_width=True, hide_index=True)