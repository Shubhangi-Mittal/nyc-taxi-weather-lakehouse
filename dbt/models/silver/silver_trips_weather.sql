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
)

select
    t.*,
    w.temperature_c,
    w.precipitation_mm,
    w.snowfall_cm,
    w.wind_speed_kmh
from trips t
left join weather w on t.pickup_hour_key = w.weather_hour_key