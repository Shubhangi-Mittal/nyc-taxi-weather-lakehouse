select
    service_type,
    pickup_borough                 as borough,
    {{ day_name('pickup_at') }}    as day_of_week,
    {{ hour_of_day('pickup_at') }} as hour_of_day,
    count(*)                       as trips
from {{ ref('silver_trips_weather') }}
where pickup_borough is not null
group by 1, 2, 3, 4