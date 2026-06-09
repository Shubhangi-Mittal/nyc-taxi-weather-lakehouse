select
    LocationID   as location_id,
    Borough      as borough,
    Zone         as zone_name,
    service_zone as service_zone
from {{ source('bronze', 'taxi_zones') }}