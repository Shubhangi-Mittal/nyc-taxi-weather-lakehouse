with source as (
    select * from {{ source('bronze', 'yellow_trips') }}
)

select
    tpep_pickup_datetime                               as pickup_at,
    tpep_dropoff_datetime                              as dropoff_at,
    date_format(tpep_pickup_datetime, 'yyyy-MM-dd HH') as pickup_hour_key,  -- join key to weather
    passenger_count,
    trip_distance                                      as trip_distance_mi,
    payment_type,
    fare_amount                                        as fare_usd,
    tip_amount                                         as tip_usd,
    total_amount                                       as total_usd
from source
where tpep_pickup_datetime >= '2024-01-01'        -- drop stray rows dated outside the month
  and tpep_pickup_datetime <  '2024-02-01'
  and trip_distance > 0 and trip_distance < 100   -- drop GPS errors / impossible distances
  and fare_amount >= 0                            -- drop refunds / negative-fare data errors
  and tpep_dropoff_datetime > tpep_pickup_datetime