with source as (
    select * from {{ source('bronze', 'green_trips') }}
)

select
    'green'                                as service_type,
    lpep_pickup_datetime                   as pickup_at,
    lpep_dropoff_datetime                  as dropoff_at,
    {{ hour_key('lpep_pickup_datetime') }} as pickup_hour_key,
    PULocationID                           as pickup_location_id,
    DOLocationID                           as dropoff_location_id,
    passenger_count,
    trip_distance                          as trip_distance_mi,
    payment_type,
    fare_amount                            as fare_usd,
    tip_amount                             as tip_usd
from source
where lpep_pickup_datetime >= '2024-01-01'
  and lpep_pickup_datetime <  '2025-01-01'
  and trip_distance > 0 and trip_distance < 100
  and fare_amount >= 0
  and lpep_dropoff_datetime > lpep_pickup_datetime