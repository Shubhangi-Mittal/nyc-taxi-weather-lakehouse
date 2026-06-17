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
def get_client():
    try:
        sa = dict(st.secrets["gcp_service_account"])
    except Exception:
        sa = None
    if sa:
        creds = service_account.Credentials.from_service_account_info(sa)
        return bigquery.Client(credentials=creds, project=PROJECT)
    return bigquery.Client(project=PROJECT)


@st.cache_data(ttl=600)
def load(table):
    return get_client().query(f"SELECT * FROM `{PROJECT}.{DATASET}.{table}`").to_dataframe()


HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "taxi_zones.geojson")) as f:
    GEO = json.load(f)

zms = load("gold_zone_month_service")
zms["pickup_location_id"] = zms["pickup_location_id"].astype(str)
hd = load("gold_hour_dow")
weather = load("gold_month_weather")

LABELS = {"yellow": "Yellow taxi", "green": "Green taxi"}
BOROUGHS = ["Manhattan", "Queens", "Brooklyn", "Bronx", "Staten Island", "EWR", "Unknown"]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

st.title("NYC Taxi & Weather Lakehouse")
st.caption("Yellow + green taxi trips · hourly weather · zone geography · 2024 · dual-cloud (Iceberg + BigQuery)")

# ---- Filters ----
svc_avail = [s for s in ["yellow", "green"] if s in set(zms["service_type"])]
svc = st.sidebar.multiselect("Service", svc_avail, default=svc_avail, format_func=lambda s: LABELS.get(s, s))
bor_avail = [b for b in BOROUGHS if b in set(zms["borough"])]
bor = st.sidebar.multiselect("Borough", bor_avail, default=bor_avail)
if not svc or not bor:
    st.warning("Select at least one service and one borough.")
    st.stop()

fz = zms[zms["service_type"].isin(svc) & zms["borough"].isin(bor)].copy()
fh = hd[hd["service_type"].isin(svc) & hd["borough"].isin(bor)].copy()
months = sorted(fz["pickup_month"].unique())
total = int(fz["trips"].sum())

# ---- KPIs ----
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total trips", f"{total:,}")
c2.metric("Avg fare", f"${fz['total_fare_usd'].sum() / total:.2f}" if total else "-")
c3.metric("Busiest zone", fz.groupby("zone_name")["trips"].sum().idxmax() if total else "-")
c4.metric("Showing", f"{len(svc)} svc · {len(bor)} boroughs")

tab_map, tab_trends, tab_patterns, tab_weather = st.tabs(["Map", "Trends", "Patterns", "Weather"])

# ---- MAP ----
with tab_map:
    sel = st.select_slider("Month", options=["Full year"] + months, value="Full year")
    src = fz if sel == "Full year" else fz[fz["pickup_month"] == sel]
    m = src.groupby(["pickup_location_id", "zone_name", "borough"], as_index=False).agg(
        trips=("trips", "sum"), total_fare_usd=("total_fare_usd", "sum"))
    m["avg_fare_usd"] = (m["total_fare_usd"] / m["trips"]).round(2)
    metric = st.radio("Colour by", ["Trips", "Avg fare"], horizontal=True)
    col = "trips" if metric == "Trips" else "avg_fare_usd"
    pm = fz.groupby(["pickup_location_id", "pickup_month"], as_index=False).agg(
        trips=("trips", "sum"), total_fare_usd=("total_fare_usd", "sum"))
    pm["avg_fare_usd"] = pm["total_fare_usd"] / pm["trips"]
    cmax = float(pm[col].quantile(0.97)) if len(pm) else 1.0
    fig = px.choropleth_map(
        m, geojson=GEO, locations="pickup_location_id", featureidkey="properties.location_id",
        color=col, color_continuous_scale="Plasma", range_color=[0, cmax],
        map_style="carto-positron", center={"lat": 40.72, "lon": -73.95}, zoom=8.6,
        opacity=0.65, hover_name="zone_name", hover_data={"pickup_location_id": False, "borough": True})
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=600)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Drag the slider to scrub through 2024.")

# ---- TRENDS ----
with tab_trends:
    bm = fz.groupby(["borough", "pickup_month"], as_index=False).agg(
        trips=("trips", "sum"), total_fare_usd=("total_fare_usd", "sum"))
    bm["avg_fare_usd"] = (bm["total_fare_usd"] / bm["trips"]).round(2)
    order = [b for b in BOROUGHS if b in set(bm["borough"])]

    st.markdown("**Borough trip race** — press ▶")
    fig = px.bar(bm, x="borough", y="trips", color="borough", animation_frame="pickup_month",
                 range_y=[0, bm["trips"].max() * 1.1],
                 category_orders={"borough": order, "pickup_month": months})
    fig.update_xaxes(title=""); fig.update_yaxes(title="Trips")
    fig.update_layout(showlegend=False, height=470)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Volume vs. fare by borough** — each bubble a borough, press ▶")
    fig2 = px.scatter(bm, x="trips", y="avg_fare_usd", size="trips", color="borough",
                      animation_frame="pickup_month", hover_name="borough", size_max=55,
                      range_x=[0, bm["trips"].max() * 1.1], range_y=[0, bm["avg_fare_usd"].max() * 1.2],
                      category_orders={"borough": order, "pickup_month": months})
    fig2.update_xaxes(title="Trips"); fig2.update_yaxes(title="Avg fare ($)")
    fig2.update_layout(height=470)
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("**Busiest pickup zones**")
    top = fz.groupby("zone_name", as_index=False)["trips"].sum().sort_values("trips").tail(15)
    figt = px.bar(top, x="trips", y="zone_name", orientation="h")
    figt.update_yaxes(title=""); figt.update_xaxes(title="Trips"); figt.update_layout(height=460)
    st.plotly_chart(figt, use_container_width=True)

# ---- PATTERNS ----
with tab_patterns:
    st.markdown("**When do New Yorkers ride?** Trips by hour of day and day of week.")
    grid = fh.groupby(["day_of_week", "hour_of_day"], as_index=False)["trips"].sum()
    pivot = grid.pivot(index="day_of_week", columns="hour_of_day", values="trips").reindex(DAYS)
    fig = px.imshow(pivot, color_continuous_scale="Magma", aspect="auto",
                    labels={"x": "Hour of day", "y": "", "color": "Trips"})
    fig.update_layout(height=420)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Bright bands = weekday rush hours and Friday/Saturday nights.")

    by_hour = fh.groupby("hour_of_day", as_index=False)["trips"].sum()
    figh = px.area(by_hour, x="hour_of_day", y="trips", title="Trips by hour of day")
    figh.update_xaxes(title="Hour"); figh.update_yaxes(title="Trips")
    st.plotly_chart(figh, use_container_width=True)

# ---- WEATHER ----
with tab_weather:
    st.markdown("Tipping holds near **25%** in clear, rain, and snow alike — January's rain 'bonus' "
                "was noise, not behaviour. *(Card tips, yellow + green; not borough-filtered.)*")
    w = weather.groupby("weather_condition", as_index=False).agg(
        trips=("trips", "sum"), card_fare_usd=("card_fare_usd", "sum"), card_tip_usd=("card_tip_usd", "sum"))
    w["tip_pct"] = (100 * w["card_tip_usd"] / w["card_fare_usd"]).round(1)
    a, b = st.columns(2)
    with a:
        fig = px.bar(w, x="weather_condition", y="tip_pct", color="weather_condition", text="tip_pct")
        fig.update_yaxes(range=[0, 35], title="Card tip %"); fig.update_xaxes(title="")
        fig.update_layout(showlegend=False); st.plotly_chart(fig, use_container_width=True)
    with b:
        fig = px.bar(w, x="weather_condition", y="trips", color="weather_condition")
        fig.update_xaxes(title=""); fig.update_yaxes(title="Trips")
        fig.update_layout(showlegend=False); st.plotly_chart(fig, use_container_width=True)