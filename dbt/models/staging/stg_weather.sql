select
    {{ parse_weather_ts('time') }} as observed_at,
    temperature_2m                 as temperature_c,
    precipitation                  as precipitation_mm,
    snowfall                       as snowfall_cm,
    wind_speed_10m                 as wind_speed_kmh
from {{ source('bronze', 'weather') }}