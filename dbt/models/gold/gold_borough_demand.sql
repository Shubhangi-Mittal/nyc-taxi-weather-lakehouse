with trips as (
    select
        pickup_borough,
        fare_usd,
        tip_usd,
        payment_type,
        trip_distance_mi
    from {{ ref('silver_trips_weather') }}
    where pickup_borough is not null
)

select
    pickup_borough,
    count(*)                                                    as trips,
    round(100.0 * count(*) / sum(count(*)) over (), 1)          as pct_of_trips,
    round(avg(trip_distance_mi), 2)                             as avg_trip_distance_mi,
    round(avg(fare_usd), 2)                                     as avg_fare_usd,
    round(avg(case when payment_type = 1
                   then 100 * tip_usd / nullif(fare_usd, 0) end), 1) as avg_tip_pct_card
from trips
group by pickup_borough
order by trips desc