{% if target.type == 'spark' %}
  {{ config(
      materialized='incremental',
      incremental_strategy='insert_overwrite',
      partition_by=['pickup_month'],
      file_format='iceberg'
  ) }}
{% else %}
  {{ config(materialized='table') }}
{% endif %}

with trips as (
    select * from {{ ref('stg_yellow') }}
),
weather as (
    select
        {{ hour_key('observed_at') }} as weather_hour_key,
        temperature_c,
        precipitation_mm,
        snowfall_cm,
        wind_speed_kmh
    from {{ ref('stg_weather') }}
),
zones as (
    select * from {{ ref('stg_zones') }}
)

select
    t.*,
    w.temperature_c,
    w.precipitation_mm,
    w.snowfall_cm,
    w.wind_speed_kmh,
    puz.borough   as pickup_borough,
    puz.zone_name as pickup_zone,
    doz.borough   as dropoff_borough,
    doz.zone_name as dropoff_zone,
    {{ month_key('t.pickup_at') }} as pickup_month
from trips t
left join weather w  on t.pickup_hour_key      = w.weather_hour_key
left join zones puz  on t.pickup_location_id    = puz.location_id
left join zones doz  on t.dropoff_location_id   = doz.location_id
{% if is_incremental() %}
where {{ month_key('t.pickup_at') }} >= (select max(pickup_month) from {{ this }})
{% endif %}