"""
NYC Taxi & Weather Lakehouse - interactive dashboard (BigQuery gold tables).
Run locally:  streamlit run dashboard/app.py
"""
import json
import os

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
    return get_client().query(f"SELECT * FROM `{PROJECT}.{DATASET}.{table}`").to_dataframe()


HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "taxi_zones.geojson")) as f:
    GEO = json.load(f)

zms = load("gold_zone_month_service")
zms["pickup_location_id"] = zms["pickup_location_id"].astype(str)
weather = load("gold_month_weather")

LABELS = {"yellow": "Yellow taxi", "green": "Green taxi"}
BOROUGHS = ["Manhattan", "Queens", "Brooklyn", "Bronx", "Staten Island", "EWR", "Unknown"]

st.title("NYC Taxi & Weather Lakehouse")
st.caption("Yellow + green taxi trips joined to hourly weather and zone geography · 2024 · "
           "dual-cloud (Iceberg + BigQuery)")

# ---- Service filter ----
avail = [s for s in ["yellow", "green"] if s in set(zms["service_type"])]
picked = st.sidebar.multiselect("Service", avail, default=avail,
                                format_func=lambda s: LABELS.get(s, s))
if not picked:
    st.warning("Pick at least one service.")
    st.stop()
fz = zms[zms["service_type"].isin(picked)].copy()
months = sorted(fz["pickup_month"].unique())

# ---- KPIs ----
total = int(fz["trips"].sum())
c1, c2, c3 = st.columns(3)
c1.metric("Total trips (2024)", f"{total:,}")
c2.metric("Avg fare", f"${fz['total_fare_usd'].sum() / total:.2f}")
c3.metric("Showing", ", ".join(LABELS[s] for s in picked))

tab_map, tab_trends, tab_weather = st.tabs(["Map", "Trends", "Weather"])

# ---- MAP: scrub through months ----
with tab_map:
    sel = st.select_slider("Month", options=["Full year"] + months, value="Full year")
    src = fz if sel == "Full year" else fz[fz["pickup_month"] == sel]
    m = src.groupby(["pickup_location_id", "zone_name", "borough"], as_index=False).agg(
        trips=("trips", "sum"), total_fare_usd=("total_fare_usd", "sum"))
    m["avg_fare_usd"] = (m["total_fare_usd"] / m["trips"]).round(2)

    metric = st.radio("Color by", ["Trips", "Avg fare"], horizontal=True)
    col = "trips" if metric == "Trips" else "avg_fare_usd"
    # fixed colour ceiling so months are visually comparable as you scrub
    per_month = fz.groupby(["pickup_location_id", "pickup_month"], as_index=False).agg(
        trips=("trips", "sum"), total_fare_usd=("total_fare_usd", "sum"))
    per_month["avg_fare_usd"] = per_month["total_fare_usd"] / per_month["trips"]
    cmax = float(per_month[col].quantile(0.97))

    fig = px.choropleth_map(
        m, geojson=GEO, locations="pickup_location_id",
        featureidkey="properties.location_id", color=col,
        color_continuous_scale="Plasma", range_color=[0, cmax],
        map_style="carto-positron", center={"lat": 40.72, "lon": -73.95},
        zoom=8.6, opacity=0.65, hover_name="zone_name",
        hover_data={"pickup_location_id": False, "borough": True},
    )
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=620)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Drag the slider to scrub through 2024. Yellow clusters in Manhattan; "
               "green spreads into the outer boroughs.")

# ---- TRENDS: animated ----
with tab_trends:
    bm = fz.groupby(["borough", "pickup_month"], as_index=False)["trips"].sum()
    order = [b for b in BOROUGHS if b in set(bm["borough"])]
    fig = px.bar(bm, x="borough", y="trips", color="borough",
                 animation_frame="pickup_month", range_y=[0, bm["trips"].max() * 1.1],
                 category_orders={"borough": order, "pickup_month": months},
                 title="Trips by borough — press ▶ to animate across 2024")
    fig.update_xaxes(title=""); fig.update_yaxes(title="Trips")
    fig.update_layout(showlegend=False, height=520)
    st.plotly_chart(fig, use_container_width=True)

    vol = fz.groupby("pickup_month", as_index=False)["trips"].sum()
    fig2 = px.line(vol, x="pickup_month", y="trips", markers=True, title="Monthly trip volume")
    fig2.update_xaxes(title=""); fig2.update_yaxes(title="Trips")
    st.plotly_chart(fig2, use_container_width=True)

# ---- WEATHER: the noise-vs-signal finding ----
with tab_weather:
    st.markdown("Tipping holds near **25%** in clear, rain, and snow alike. One month suggested a "
                "rain bonus; a full year showed it was noise. *(Card tips, yellow + green.)*")
    w = weather.groupby("weather_condition", as_index=False).agg(
        trips=("trips", "sum"), card_fare_usd=("card_fare_usd", "sum"),
        card_tip_usd=("card_tip_usd", "sum"))
    w["tip_pct"] = (100 * w["card_tip_usd"] / w["card_fare_usd"]).round(1)
    a, b = st.columns(2)
    with a:
        fig = px.bar(w, x="weather_condition", y="tip_pct", color="weather_condition", text="tip_pct")
        fig.update_yaxes(range=[0, 35], title="Card tip %"); fig.update_xaxes(title="")
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    with b:
        fig = px.bar(w, x="weather_condition", y="trips", color="weather_condition")
        fig.update_xaxes(title=""); fig.update_yaxes(title="Trips")
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)