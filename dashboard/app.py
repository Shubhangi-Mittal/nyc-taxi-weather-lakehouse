"""
NYC Taxi & Weather Lakehouse - interactive dashboard over the gold tables (BigQuery).
Run locally:  streamlit run dashboard/app.py
"""

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


SEASON = {12: "Winter", 1: "Winter", 2: "Winter",
          3: "Spring", 4: "Spring", 5: "Spring",
          6: "Summer", 7: "Summer", 8: "Summer",
          9: "Fall", 10: "Fall", 11: "Fall"}
GRAINS = {
    "Monthly":   ("pickup_month", None),
    "Quarterly": ("quarter", ["Q1", "Q2", "Q3", "Q4"]),
    "Seasonal":  ("season", ["Winter", "Spring", "Summer", "Fall"]),
}

base = load("gold_month_weather").copy()
base["month_num"] = base["pickup_month"].str[-2:].astype(int)
base["quarter"] = "Q" + ((base["month_num"] - 1) // 3 + 1).astype(str)
base["season"] = base["month_num"].map(SEASON)
borough = load("gold_borough_demand")


def rollup(df: pd.DataFrame, by: str) -> pd.DataFrame:
    g = df.groupby([by, "weather_condition"], as_index=False).agg(
        trips=("trips", "sum"),
        total_distance_mi=("total_distance_mi", "sum"),
        total_fare_usd=("total_fare_usd", "sum"),
        card_fare_usd=("card_fare_usd", "sum"),
        card_tip_usd=("card_tip_usd", "sum"),
    )
    g["avg_fare_usd"] = (g["total_fare_usd"] / g["trips"]).round(2)
    g["tip_pct_card"] = (100 * g["card_tip_usd"] / g["card_fare_usd"].replace(0, float("nan"))).round(2)
    return g


def ordered(df: pd.DataFrame, col: str, order) -> pd.DataFrame:
    if order:
        df[col] = pd.Categorical(df[col], categories=order, ordered=True)
    return df.sort_values(col)


# ---- Header + KPIs ------------------------------------------------------
st.title("NYC Taxi & Weather Lakehouse")
st.caption("Yellow-taxi trips joined to hourly NYC weather · full-year 2024 · ~40M trips · "
           "dual-cloud (Iceberg + BigQuery)")

total_trips = int(base["trips"].sum())
yr = base.groupby("weather_condition")[["card_fare_usd", "card_tip_usd"]].sum()
yr["tip"] = 100 * yr["card_tip_usd"] / yr["card_fare_usd"]
annual_gap = yr.loc["rain", "tip"] - yr.loc["clear", "tip"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total trips (2024)", f"{total_trips:,}")
c2.metric("Avg fare", f"${base['total_fare_usd'].sum() / total_trips:.2f}")
c3.metric("Card tip %", f"{100 * base['card_tip_usd'].sum() / base['card_fare_usd'].sum():.1f}%")
c4.metric("Rain vs clear tip gap", f"{annual_gap:+.1f} pts", help="Full-year. ~0 = no real effect.")

# ---- Filter -------------------------------------------------------------
grain_label = st.sidebar.radio("Time granularity", list(GRAINS.keys()))
grain_col, order = GRAINS[grain_label]
g = ordered(rollup(base, grain_col), grain_col, order)

# ---- Noise vs signal ----------------------------------------------------
st.subheader(f"Does weather move tipping? ({grain_label.lower()})")
st.markdown(
    "Across the full year, tipping holds near **25%** in every condition. The right-hand "
    "chart shows the rain-vs-clear tip gap swinging around **zero** period to period — "
    "January's +3 points was an outlier, not a pattern. Scaling from one month to a full "
    "year turned an exciting-but-fake finding into an honest one."
)

pivot = g.pivot_table(index=grain_col, columns="weather_condition",
                      values="tip_pct_card", observed=True)
gap = (pivot["rain"] - pivot["clear"]).reset_index(name="rain_minus_clear")

a, b = st.columns(2)
with a:
    fig = px.line(g, x=grain_col, y="tip_pct_card", color="weather_condition",
                  markers=True, title="Card tip % by weather")
    fig.update_yaxes(range=[20, 32], title="Tip %")
    fig.update_xaxes(title="")
    st.plotly_chart(fig, use_container_width=True)
with b:
    fig = px.bar(gap, x=grain_col, y="rain_minus_clear", title="Rain − clear tip gap")
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.update_yaxes(title="Points")
    fig.update_xaxes(title="")
    st.plotly_chart(fig, use_container_width=True)

# ---- Volume + fares -----------------------------------------------------
st.subheader(f"Trips and fares ({grain_label.lower()})")
vol = ordered(base.groupby(grain_col, as_index=False).agg(
    trips=("trips", "sum"), total_fare_usd=("total_fare_usd", "sum")), grain_col, order)
vol["avg_fare_usd"] = (vol["total_fare_usd"] / vol["trips"]).round(2)

a, b = st.columns(2)
with a:
    fig = px.bar(vol, x=grain_col, y="trips", title="Trip volume")
    fig.update_xaxes(title=""); fig.update_yaxes(title="Trips")
    st.plotly_chart(fig, use_container_width=True)
with b:
    fig = px.line(vol, x=grain_col, y="avg_fare_usd", markers=True, title="Average fare")
    fig.update_xaxes(title=""); fig.update_yaxes(title="USD")
    st.plotly_chart(fig, use_container_width=True)

# ---- Borough ------------------------------------------------------------
st.subheader("Pickups by borough (full year)")
fig = px.bar(borough.sort_values("trips"), x="trips", y="pickup_borough", orientation="h")
fig.update_yaxes(title=""); fig.update_xaxes(title="Trips")
st.plotly_chart(fig, use_container_width=True)