select
    pickup_location_id,
    max(pickup_zone)    as zone_name,
    max(pickup_borough) as borough,
    count(*)            as trips,
    round(avg(fare_usd), 2) as avg_fare_usd,
    round(avg(case when payment_type = 1
                   then 100 * tip_usd / nullif(fare_usd, 0) end), 1) as avg_tip_pct_card
from {{ ref('silver_trips_weather') }}
where pickup_location_id is not null
group by pickup_location_id