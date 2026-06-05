with classified as (
    select
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
    weather_condition,
    count(*)                                  as trips,
    round(avg(trip_distance_mi), 2)           as avg_trip_distance_mi,
    round(avg(fare_usd), 2)                    as avg_fare_usd,
    -- tips are only recorded for card payments (payment_type = 1):
    round(avg(case when payment_type = 1
                   then 100 * tip_usd / nullif(fare_usd, 0) end), 1) as avg_tip_pct_card
from classified
group by weather_condition
order by trips desc