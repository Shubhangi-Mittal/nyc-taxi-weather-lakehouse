select
    pickup_month,
    count(*)                          as trips,
    round(avg(trip_distance_mi), 2)   as avg_trip_distance_mi,
    round(avg(fare_usd), 2)           as avg_fare_usd
from {{ ref('silver_trips_weather') }}
group by pickup_month
order by pickup_month