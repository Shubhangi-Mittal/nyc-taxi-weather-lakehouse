with source as (
    select * from {{ source('bronze', 'yellow_trips') }}
)

select
    tpep_pickup_datetime                   as pickup_at,
    tpep_dropoff_datetime                  as dropoff_at,
    {{ hour_key('tpep_pickup_datetime') }} as pickup_hour_key,
    passenger_count,
    trip_distance                          as trip_distance_mi,
    payment_type,
    fare_amount                            as fare_usd,
    tip_amount                             as tip_usd,
    total_amount                           as total_usd
from source
where tpep_pickup_datetime >= '2024-01-01'
  and tpep_pickup_datetime <  '2024-02-01'
  and trip_distance > 0 and trip_distance < 100
  and fare_amount >= 0
  and tpep_dropoff_datetime > tpep_pickup_datetime