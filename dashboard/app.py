"""
NYC Taxi & Weather Lakehouse - interactive dashboard (BigQuery gold tables).
Run locally: streamlit run dashboard/app.py
"""
import json
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account
from plotly.subplots import make_subplots

PROJECT = "nyc-lakehouse"
DATASET = "lakehouse"

st.set_page_config(
    page_title="NYC Taxi & Weather Lakehouse",
    page_icon="🚕",
    layout="wide",
    initial_sidebar_state="expanded",
)


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
    query = f"SELECT * FROM `{PROJECT}.{DATASET}.{table}`"
    return get_client().query(query).to_dataframe()


@st.cache_data(ttl=600)
def load_all():
    zone_month_service = load("gold_zone_month_service")
    hour_dow = load("gold_hour_dow")
    month_weather = load("gold_month_weather")
    zone_demand = load("gold_zone_demand")
    borough_demand = load("gold_borough_demand")
    return zone_month_service, hour_dow, month_weather, zone_demand, borough_demand


def month_labels(values):
    series = pd.Series(values).dropna().astype(str)
    parsed = pd.to_datetime(series, errors="coerce")
    labels = []
    for raw, dt in zip(series, parsed):
        labels.append(dt.strftime("%b %Y") if pd.notna(dt) else raw)
    return dict(zip(series.tolist(), labels))


def metric_delta(current, baseline):
    if baseline in (0, None) or pd.isna(baseline):
        return None
    return round(100 * (current - baseline) / baseline, 1)


def humanize_int(value):
    return f"{int(value):,}" if pd.notna(value) else "-"


def humanize_money(value):
    return f"${value:,.2f}" if pd.notna(value) else "-"


def theme_chart(fig):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(247,243,233,0.55)",
        font={"family": "Arial", "color": "#192126"},
        margin={"l": 16, "r": 16, "t": 44, "b": 16},
        hoverlabel={"bgcolor": "#fffaf2", "font_size": 13, "font_family": "Arial"},
        transition={"duration": 550, "easing": "cubic-in-out"},
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="rgba(25,33,38,0.08)", zeroline=False)
    return fig


st.markdown(
    """
    <style>
      .stApp {
        background:
          radial-gradient(circle at top left, rgba(255, 180, 96, 0.26), transparent 24%),
          radial-gradient(circle at top right, rgba(87, 166, 173, 0.25), transparent 28%),
          linear-gradient(180deg, #f6efe2 0%, #f3f5f0 42%, #edf1ef 100%);
      }
      [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #16232a 0%, #233841 100%);
      }
      [data-testid="stSidebar"] * {
        color: #f7f2e9;
      }
      .hero {
        padding: 1.6rem 1.8rem;
        border-radius: 28px;
        background: linear-gradient(135deg, rgba(17, 27, 31, 0.94), rgba(34, 56, 65, 0.90));
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 24px 60px rgba(22, 35, 42, 0.18);
        color: #f8f4eb;
        margin-bottom: 1rem;
        animation: rise 0.8s ease-out;
      }
      .hero h1 {
        margin: 0 0 0.35rem 0;
        font-size: 2.35rem;
        line-height: 1.05;
      }
      .hero p {
        margin: 0;
        font-size: 1rem;
        color: rgba(248, 244, 235, 0.82);
      }
      .kpi-card {
        background: rgba(255, 250, 242, 0.88);
        border: 1px solid rgba(25, 33, 38, 0.08);
        border-radius: 22px;
        padding: 1rem 1.1rem;
        box-shadow: 0 16px 36px rgba(37, 52, 56, 0.08);
        min-height: 128px;
        animation: rise 0.7s ease-out;
      }
      .kpi-label {
        color: #52626a;
        font-size: 0.84rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.3rem;
      }
      .kpi-value {
        color: #16232a;
        font-size: 1.9rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
      }
      .kpi-subtle {
        color: #6d7779;
        font-size: 0.95rem;
      }
      .section-note {
        padding: 0.9rem 1rem;
        border-radius: 18px;
        background: rgba(255, 250, 242, 0.82);
        border: 1px solid rgba(25, 33, 38, 0.07);
        color: #4b5e65;
      }
      @keyframes rise {
        from { opacity: 0; transform: translateY(16px); }
        to { opacity: 1; transform: translateY(0); }
      }
      div[data-testid="stMetric"] {
        background: rgba(255, 250, 242, 0.72);
        border: 1px solid rgba(25, 33, 38, 0.08);
        border-radius: 20px;
        padding: 0.9rem 1rem;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "taxi_zones.geojson")) as f:
    GEO = json.load(f)

zms, hd, weather, zone_demand, borough_demand = load_all()

zms["pickup_location_id"] = zms["pickup_location_id"].astype(str)
zone_demand["pickup_location_id"] = zone_demand["pickup_location_id"].astype(str)
month_map = month_labels(sorted(zms["pickup_month"].dropna().astype(str).unique()))
month_options = list(month_map.keys())
service_labels = {"yellow": "Yellow taxi", "green": "Green taxi"}
borough_order = ["Manhattan", "Queens", "Brooklyn", "Bronx", "Staten Island", "EWR", "Unknown"]
day_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
zone_base = zone_demand.rename(columns={"trips": "all_trips", "avg_fare_usd": "all_avg_fare_usd"})
borough_base = borough_demand.rename(columns={"pickup_borough": "borough"})

st.markdown(
    """
    <div class="hero">
      <h1>NYC Taxi x Weather Observatory</h1>
      <p>Explore how service mix, geography, time of day, and weather shape taxi demand across New York City in 2024.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "Yellow + green taxi trips · hourly weather joins · zone geography · BigQuery gold marts · interactive Streamlit experience"
)

with st.sidebar:
    st.markdown("### Explore")
    selected_services = st.multiselect(
        "Service type",
        options=[s for s in ["yellow", "green"] if s in set(zms["service_type"])],
        default=[s for s in ["yellow", "green"] if s in set(zms["service_type"])],
        format_func=lambda s: service_labels.get(s, s.title()),
    )
    selected_boroughs = st.multiselect(
        "Borough",
        options=[b for b in borough_order if b in set(zms["borough"])],
        default=[b for b in borough_order if b in set(zms["borough"])],
    )
    selected_months = st.select_slider(
        "Month window",
        options=month_options,
        value=(month_options[0], month_options[-1]),
        format_func=lambda m: month_map.get(m, m),
    )
    selected_metric = st.radio(
        "Map focus",
        options=["Trips", "Average fare", "Market share"],
        horizontal=False,
    )
    top_n = st.slider("Top zones to highlight", min_value=5, max_value=20, value=10)

if not selected_services or not selected_boroughs:
    st.warning("Select at least one service and one borough to render the dashboard.")
    st.stop()

month_start, month_end = selected_months
active_months = [m for m in month_options if month_start <= m <= month_end]
zms_f = zms[
    zms["service_type"].isin(selected_services)
    & zms["borough"].isin(selected_boroughs)
    & zms["pickup_month"].astype(str).isin(active_months)
].copy()
hd_f = hd[
    hd["service_type"].isin(selected_services)
    & hd["borough"].isin(selected_boroughs)
].copy()
zone_f = zone_base[zone_base["borough"].isin(selected_boroughs)].copy()
borough_f = borough_base[borough_base["borough"].isin(selected_boroughs)].copy()

if zms_f.empty:
    st.warning("No rows match the current filter combination.")
    st.stop()

total_trips = int(zms_f["trips"].sum())
total_fare = float(zms_f["total_fare_usd"].sum())
avg_fare = total_fare / total_trips if total_trips else 0
zones_ranked = zms_f.groupby("zone_name", as_index=False)["trips"].sum().sort_values("trips", ascending=False)
busiest_zone = zones_ranked.iloc[0]["zone_name"] if not zones_ranked.empty else "-"
month_trend = zms_f.groupby("pickup_month", as_index=False).agg(trips=("trips", "sum"), fare=("total_fare_usd", "sum"))
month_trend["avg_fare_usd"] = month_trend["fare"] / month_trend["trips"]
peak_month = month_trend.sort_values("trips", ascending=False).iloc[0] if not month_trend.empty else None
service_mix = zms_f.groupby("service_type", as_index=False)["trips"].sum()
yellow_share = (
    100 * service_mix.loc[service_mix["service_type"] == "yellow", "trips"].sum() / total_trips if total_trips else 0
)
city_avg_fare = zone_f["all_avg_fare_usd"].mean() if not zone_f.empty else None
avg_fare_delta = metric_delta(avg_fare, city_avg_fare)
avg_fare_delta_text = f"{avg_fare_delta:+.1f}%" if avg_fare_delta is not None else "n/a"

k1, k2, k3, k4 = st.columns(4)
k1.markdown(
    f"""
    <div class="kpi-card">
      <div class="kpi-label">Trips in view</div>
      <div class="kpi-value">{humanize_int(total_trips)}</div>
      <div class="kpi-subtle">{len(active_months)} month(s) · {len(selected_boroughs)} borough(s)</div>
    </div>
    """,
    unsafe_allow_html=True,
)
k2.markdown(
    f"""
    <div class="kpi-card">
      <div class="kpi-label">Average fare</div>
      <div class="kpi-value">{humanize_money(avg_fare)}</div>
      <div class="kpi-subtle">vs citywide zone avg: {avg_fare_delta_text}</div>
    </div>
    """,
    unsafe_allow_html=True,
)
k3.markdown(
    f"""
    <div class="kpi-card">
      <div class="kpi-label">Busiest zone</div>
      <div class="kpi-value" style="font-size:1.4rem;">{busiest_zone}</div>
      <div class="kpi-subtle">Most trips in the filtered view</div>
    </div>
    """,
    unsafe_allow_html=True,
)
k4.markdown(
    f"""
    <div class="kpi-card">
      <div class="kpi-label">Yellow share</div>
      <div class="kpi-value">{yellow_share:.1f}%</div>
      <div class="kpi-subtle">Share of trips from yellow taxis</div>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_overview, tab_geo, tab_patterns, tab_weather = st.tabs(
    ["Overview", "Geography", "Time Patterns", "Weather"]
)

with tab_overview:
    left, right = st.columns([1.15, 0.85])

    with left:
        overview = (
            zms_f.groupby(["pickup_month", "service_type"], as_index=False)
            .agg(trips=("trips", "sum"), fare=("total_fare_usd", "sum"))
            .sort_values("pickup_month")
        )
        overview["avg_fare_usd"] = overview["fare"] / overview["trips"]
        fig = px.line(
            overview,
            x="pickup_month",
            y="trips",
            color="service_type",
            markers=True,
            category_orders={"pickup_month": active_months},
            color_discrete_map={"yellow": "#ffb703", "green": "#2a9d8f"},
            labels={"pickup_month": "", "trips": "Trips", "service_type": "Service"},
        )
        fig.update_traces(
            line={"width": 4},
            marker={"size": 10},
            customdata=overview[["avg_fare_usd"]],
            hovertemplate="<b>%{fullData.name}</b><br>%{x}<br>Trips: %{y:,.0f}<br>Avg fare: $%{customdata[0]:.2f}<extra></extra>",
        )
        fig.update_xaxes(tickvals=active_months, ticktext=[month_map[m] for m in active_months])
        fig.update_layout(title="Monthly demand by service", legend_title_text="")
        st.plotly_chart(theme_chart(fig), use_container_width=True)

    with right:
        donut = px.pie(
            service_mix,
            names="service_type",
            values="trips",
            hole=0.62,
            color="service_type",
            color_discrete_map={"yellow": "#ffb703", "green": "#2a9d8f"},
        )
        donut.update_traces(
            textposition="inside",
            texttemplate="%{percent}",
            hovertemplate="<b>%{label}</b><br>Trips: %{value:,.0f}<br>Share: %{percent}<extra></extra>",
        )
        donut.update_layout(title="Service mix", showlegend=False, height=390)
        st.plotly_chart(theme_chart(donut), use_container_width=True)

    lower_left, lower_right = st.columns([1.05, 0.95])
    with lower_left:
        borough_month = (
            zms_f.groupby(["pickup_month", "borough"], as_index=False)["trips"].sum().sort_values("pickup_month")
        )
        fig = px.bar(
            borough_month,
            x="pickup_month",
            y="trips",
            color="borough",
            barmode="stack",
            category_orders={"pickup_month": active_months, "borough": borough_order},
            labels={"pickup_month": "", "trips": "Trips"},
        )
        fig.update_traces(
            hovertemplate="<b>%{fullData.name}</b><br>%{x}<br>Trips: %{y:,.0f}<extra></extra>"
        )
        fig.update_xaxes(tickvals=active_months, ticktext=[month_map[m] for m in active_months])
        fig.update_layout(title="Monthly demand by borough", legend_title_text="", height=420)
        st.plotly_chart(theme_chart(fig), use_container_width=True)

    with lower_right:
        top_zones = zones_ranked.head(top_n).sort_values("trips")
        fig = px.bar(
            top_zones,
            x="trips",
            y="zone_name",
            orientation="h",
            color="trips",
            color_continuous_scale=["#ffd166", "#ef476f", "#264653"],
            labels={"zone_name": "", "trips": "Trips"},
        )
        fig.update_traces(
            hovertemplate="<b>%{y}</b><br>Trips: %{x:,.0f}<extra></extra>"
        )
        fig.update_layout(title=f"Top {top_n} pickup zones", coloraxis_showscale=False, height=420)
        st.plotly_chart(theme_chart(fig), use_container_width=True)

    borough_compare = borough_f.sort_values("trips", ascending=False)
    if not borough_compare.empty:
        fig = px.scatter(
            borough_compare,
            x="avg_trip_distance_mi",
            y="avg_fare_usd",
            size="trips",
            color="borough",
            hover_name="borough",
            size_max=55,
            labels={
                "avg_trip_distance_mi": "Avg trip distance (mi)",
                "avg_fare_usd": "Avg fare ($)",
            },
        )
        fig.update_traces(
            customdata=borough_compare[["pct_of_trips", "avg_tip_pct_card"]],
            hovertemplate="<b>%{hovertext}</b><br>Avg distance: %{x:.2f} mi<br>Avg fare: $%{y:.2f}<br>Share of trips: %{customdata[0]:.1f}%<br>Avg card tip: %{customdata[1]:.1f}%<extra></extra>",
        )
        fig.update_layout(title="Borough benchmark: distance, fare, and demand share", legend_title_text="", height=380)
        st.plotly_chart(theme_chart(fig), use_container_width=True)

with tab_geo:
    map_col, insights_col = st.columns([1.45, 0.85])

    with map_col:
        geo = (
            zms_f.groupby(["pickup_location_id", "zone_name", "borough"], as_index=False)
            .agg(trips=("trips", "sum"), total_fare_usd=("total_fare_usd", "sum"))
            .merge(zone_f[["pickup_location_id", "all_trips"]], on="pickup_location_id", how="left")
        )
        geo["avg_fare_usd"] = geo["total_fare_usd"] / geo["trips"]
        geo["market_share_pct"] = 100 * geo["trips"] / geo["all_trips"]
        metric_lookup = {
            "Trips": ("trips", "Trips", [0, float(geo["trips"].quantile(0.97) or 1)]),
            "Average fare": (
                "avg_fare_usd",
                "Average fare ($)",
                [0, float(geo["avg_fare_usd"].quantile(0.97) or 1)],
            ),
            "Market share": (
                "market_share_pct",
                "Filtered share of zone demand (%)",
                [0, float(geo["market_share_pct"].quantile(0.97) or 1)],
            ),
        }
        metric_col, metric_title, metric_range = metric_lookup[selected_metric]
        fig = px.choropleth_map(
            geo,
            geojson=GEO,
            locations="pickup_location_id",
            featureidkey="properties.location_id",
            color=metric_col,
            color_continuous_scale=["#e9c46a", "#f4a261", "#e76f51", "#264653"],
            range_color=metric_range,
            map_style="carto-positron",
            center={"lat": 40.72, "lon": -73.95},
            zoom=8.65,
            opacity=0.72,
            hover_name="zone_name",
            hover_data={
                "borough": True,
                "trips": ":,",
                "avg_fare_usd": ":.2f",
                "market_share_pct": ":.1f",
                "pickup_location_id": False,
            },
            labels={
                "avg_fare_usd": "Avg fare ($)",
                "market_share_pct": "Share of zone demand (%)",
            },
        )
        fig.update_layout(
            title=f"Interactive zone map: {metric_title}",
            height=640,
            margin={"l": 0, "r": 0, "t": 44, "b": 0},
        )
        st.plotly_chart(theme_chart(fig), use_container_width=True)

    with insights_col:
        st.markdown(
            f"""
            <div class="section-note">
              <strong>Read the map</strong><br>
              Use the sidebar to change the month window, service mix, and borough coverage.
              Market share is especially helpful when you want to see how concentrated a filtered slice is inside each zone rather than just where raw volume is highest.
            </div>
            """,
            unsafe_allow_html=True,
        )

        treemap_data = (
            zms_f.groupby(["service_type", "borough", "zone_name"], as_index=False)["trips"].sum().sort_values("trips", ascending=False)
        )
        fig = px.treemap(
            treemap_data,
            path=["service_type", "borough", "zone_name"],
            values="trips",
            color="trips",
            color_continuous_scale=["#2a9d8f", "#e9c46a", "#e76f51"],
        )
        fig.update_traces(
            hovertemplate="<b>%{label}</b><br>Trips: %{value:,.0f}<br>Share of parent: %{percentParent}<extra></extra>"
        )
        fig.update_layout(title="Demand composition", coloraxis_showscale=False, height=360)
        st.plotly_chart(theme_chart(fig), use_container_width=True)

        zone_compare = (
            geo.sort_values("trips", ascending=False)
            .head(top_n)
            .sort_values("avg_fare_usd", ascending=False)
        )
        fig = px.scatter(
            zone_compare,
            x="trips",
            y="avg_fare_usd",
            size="market_share_pct",
            color="borough",
            hover_name="zone_name",
            size_max=40,
            labels={"trips": "Trips", "avg_fare_usd": "Avg fare ($)"},
        )
        fig.update_traces(
            hovertemplate="<b>%{hovertext}</b><br>Trips: %{x:,.0f}<br>Avg fare: $%{y:.2f}<br>Market share: %{marker.size:.1f}%<extra></extra>"
        )
        fig.update_layout(title="Top zones: volume vs fare", height=320, legend_title_text="")
        st.plotly_chart(theme_chart(fig), use_container_width=True)

with tab_patterns:
    p1, p2 = st.columns([1.15, 0.85])
    heat = hd_f.groupby(["day_of_week", "hour_of_day"], as_index=False)["trips"].sum()
    pivot = heat.pivot(index="day_of_week", columns="hour_of_day", values="trips").reindex(day_order).fillna(0)

    with p1:
        fig = px.imshow(
            pivot,
            color_continuous_scale=["#f8f4eb", "#f4a261", "#e76f51", "#264653"],
            aspect="auto",
            labels={"x": "Hour of day", "y": "", "color": "Trips"},
        )
        fig.update_traces(
            hovertemplate="Day: %{y}<br>Hour: %{x}:00<br>Trips: %{z:,.0f}<extra></extra>"
        )
        fig.update_layout(title="Demand heatmap: day of week x hour", height=430)
        st.plotly_chart(theme_chart(fig), use_container_width=True)

    with p2:
        hourly = hd_f.groupby(["hour_of_day", "service_type"], as_index=False)["trips"].sum()
        fig = px.area(
            hourly,
            x="hour_of_day",
            y="trips",
            color="service_type",
            color_discrete_map={"yellow": "#ffb703", "green": "#2a9d8f"},
            labels={"hour_of_day": "Hour", "trips": "Trips", "service_type": "Service"},
        )
        fig.update_traces(
            mode="lines",
            hovertemplate="<b>%{fullData.name}</b><br>%{x}:00<br>Trips: %{y:,.0f}<extra></extra>",
        )
        fig.update_layout(title="Hourly ride rhythm by service", legend_title_text="", height=430)
        st.plotly_chart(theme_chart(fig), use_container_width=True)

    pattern_left, pattern_right = st.columns([0.9, 1.1])
    with pattern_left:
        weekday_mix = hd_f.groupby("day_of_week", as_index=False)["trips"].sum()
        weekday_mix["day_of_week"] = pd.Categorical(weekday_mix["day_of_week"], categories=day_order, ordered=True)
        weekday_mix = weekday_mix.sort_values("day_of_week")
        fig = px.bar_polar(
            weekday_mix,
            r="trips",
            theta="day_of_week",
            color="trips",
            color_continuous_scale=["#2a9d8f", "#e9c46a", "#e76f51"],
        )
        fig.update_traces(hovertemplate="Day: %{theta}<br>Trips: %{r:,.0f}<extra></extra>")
        fig.update_layout(title="Weekly rhythm", coloraxis_showscale=False, height=390)
        st.plotly_chart(theme_chart(fig), use_container_width=True)

    with pattern_right:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        hourly_total = hd_f.groupby("hour_of_day", as_index=False)["trips"].sum().sort_values("hour_of_day")
        hourly_total["trip_share_pct"] = 100 * hourly_total["trips"] / hourly_total["trips"].sum()
        fig.add_trace(
            go.Bar(
                x=hourly_total["hour_of_day"],
                y=hourly_total["trips"],
                name="Trips",
                marker_color="#264653",
                hovertemplate="Hour %{x}:00<br>Trips: %{y:,.0f}<extra></extra>",
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=hourly_total["hour_of_day"],
                y=hourly_total["trip_share_pct"],
                name="Share of trips",
                line={"width": 3, "color": "#e76f51"},
                hovertemplate="Hour %{x}:00<br>Share: %{y:.2f}%<extra></extra>",
            ),
            secondary_y=True,
        )
        fig.update_layout(title="Volume and share by hour", height=390, legend_title_text="")
        fig.update_xaxes(title_text="Hour of day")
        fig.update_yaxes(title_text="Trips", secondary_y=False)
        fig.update_yaxes(title_text="Share of trips (%)", secondary_y=True)
        st.plotly_chart(theme_chart(fig), use_container_width=True)

with tab_weather:
    st.markdown(
        """
        <div class="section-note">
          Weather is shown citywide because the gold weather mart is month-level rather than borough-level.
          Use it to compare seasonal demand and card-tip behavior across clear, rainy, and snowy months.
        </div>
        """,
        unsafe_allow_html=True,
    )

    weather_plot = weather.copy()
    weather_plot["month_label"] = weather_plot["pickup_month"].astype(str).map(month_map).fillna(weather_plot["pickup_month"].astype(str))
    weather_plot["tip_pct"] = 100 * weather_plot["card_tip_usd"] / weather_plot["card_fare_usd"]
    weather_plot["fare_per_trip"] = weather_plot["total_fare_usd"] / weather_plot["trips"]
    weather_summary = weather_plot.groupby("weather_condition", as_index=False).agg(
        trips=("trips", "sum"),
        card_fare_usd=("card_fare_usd", "sum"),
        card_tip_usd=("card_tip_usd", "sum"),
        total_distance_mi=("total_distance_mi", "sum"),
    )
    weather_summary["tip_pct"] = 100 * weather_summary["card_tip_usd"] / weather_summary["card_fare_usd"]

    w1, w2 = st.columns([1.05, 0.95])
    with w1:
        fig = px.scatter(
            weather_plot,
            x="total_distance_mi",
            y="tip_pct",
            size="trips",
            color="weather_condition",
            hover_name="month_label",
            size_max=56,
            color_discrete_map={"clear": "#2a9d8f", "rain": "#f4a261", "snow": "#577590"},
            labels={"total_distance_mi": "Total trip distance (mi)", "tip_pct": "Card tip %"},
        )
        fig.update_traces(
            hovertemplate="<b>%{hovertext}</b><br>Weather: %{fullData.name}<br>Total distance: %{x:,.0f} mi<br>Card tip: %{y:.2f}%<br>Trips: %{marker.size:,.0f}<extra></extra>"
        )
        fig.update_layout(title="Monthly weather footprint", legend_title_text="", height=420)
        st.plotly_chart(theme_chart(fig), use_container_width=True)

    with w2:
        fig = px.bar(
            weather_summary.sort_values("tip_pct", ascending=False),
            x="weather_condition",
            y=["tip_pct", "trips"],
            barmode="group",
            color_discrete_sequence=["#e76f51", "#264653"],
            labels={"value": "", "variable": "Metric", "weather_condition": ""},
        )
        fig.update_layout(title="Tips and trip volume by weather", height=420, legend_title_text="")
        st.plotly_chart(theme_chart(fig), use_container_width=True)

    w3, w4 = st.columns([1.1, 0.9])
    with w3:
        month_weather_chart = weather_plot.sort_values("pickup_month")
        fig = px.line(
            month_weather_chart,
            x="pickup_month",
            y="fare_per_trip",
            color="weather_condition",
            markers=True,
            color_discrete_map={"clear": "#2a9d8f", "rain": "#f4a261", "snow": "#577590"},
            labels={"pickup_month": "", "fare_per_trip": "Fare per trip ($)", "weather_condition": "Weather"},
        )
        fig.update_traces(
            line={"width": 4},
            marker={"size": 9},
            hovertemplate="<b>%{fullData.name}</b><br>%{x}<br>Fare per trip: $%{y:.2f}<extra></extra>",
        )
        fig.update_xaxes(
            tickvals=month_weather_chart["pickup_month"].astype(str).tolist(),
            ticktext=[month_map.get(m, m) for m in month_weather_chart["pickup_month"].astype(str).tolist()],
        )
        fig.update_layout(title="Fare per trip through the year", legend_title_text="", height=390)
        st.plotly_chart(theme_chart(fig), use_container_width=True)

    with w4:
        summary_text = "Peak filtered month: "
        if peak_month is not None:
            summary_text += f"{month_map.get(str(peak_month['pickup_month']), str(peak_month['pickup_month']))} with {humanize_int(peak_month['trips'])} trips."
        else:
            summary_text += "n/a."
        st.markdown(
            f"""
            <div class="section-note">
              <strong>What stands out</strong><br>
              {summary_text}<br><br>
              Rain and snow can shift trip volume and total distance, but card-tip rates tend to stay fairly stable.
              That makes demand sensitivity more visible than tipping sensitivity in this mart.
            </div>
            """,
            unsafe_allow_html=True,
        )
