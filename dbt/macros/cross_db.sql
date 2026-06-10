{% macro hour_key(ts_column) %}
    {%- if target.type == 'spark' -%}
        date_format({{ ts_column }}, 'yyyy-MM-dd HH')
    {%- else -%}
        format_datetime('%Y-%m-%d %H', cast({{ ts_column }} as datetime))
    {%- endif -%}
{% endmacro %}

{% macro month_key(ts_column) %}
    {%- if target.type == 'spark' -%}
        date_format({{ ts_column }}, 'yyyy-MM')
    {%- else -%}
        format_datetime('%Y-%m', cast({{ ts_column }} as datetime))
    {%- endif -%}
{% endmacro %}

{% macro parse_weather_ts(str_column) %}
    {%- if target.type == 'spark' -%}
        to_timestamp({{ str_column }}, "yyyy-MM-dd'T'HH:mm")
    {%- else -%}
        cast({{ str_column }} as datetime)
    {%- endif -%}
{% endmacro %}