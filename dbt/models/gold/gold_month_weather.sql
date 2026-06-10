with classified as (
    select
        pickup_month,
        case
            when snowfall_cm > 0      then 'snow'
            when precipitation_mm > 0 then 'rain'
            else 'clear'
        end as weather_condition,
        trip_distance_mi,
        fare_usd,
        tip_usd,
        payment_type
    from {{ ref('silver_trips_weather') }}
)

select
    pickup_month,
    weather_condition,
    count(*)                                                           as trips,
    round(sum(trip_distance_mi), 1)                                   as total_distance_mi,
    round(sum(fare_usd), 1)                                           as total_fare_usd,
    round(sum(case when payment_type = 1 then fare_usd else 0 end), 1) as card_fare_usd,
    round(sum(case when payment_type = 1 then tip_usd  else 0 end), 1) as card_tip_usd
from classified
group by pickup_month, weather_condition
order by pickup_month, weather_condition