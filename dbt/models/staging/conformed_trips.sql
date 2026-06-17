{{ config(materialized='view') }}

select * from {{ ref('stg_yellow') }}
union all
select * from {{ ref('stg_green') }}