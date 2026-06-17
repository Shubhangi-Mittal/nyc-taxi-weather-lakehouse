select
    pickup_location_id,
    max(pickup_zone)    as zone_name,
    max(pickup_borough) as borough,
    pickup_month,
    service_type,
    count(*)            as trips,
    round(sum(fare_usd), 1) as total_fare_usd
from {{ ref('silver_trips_weather') }}
where pickup_location_id is not null
group by pickup_location_id, pickup_month, service_type