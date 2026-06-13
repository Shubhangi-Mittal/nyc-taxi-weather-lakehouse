import geopandas as gpd

zones = gpd.read_file("taxi_zones_shp/taxi_zones.shp")
if zones.crs is None:
    zones = zones.set_crs(epsg=2263)          # TLC ships NY State Plane (feet)
zones = zones.to_crs(epsg=4326)               # web maps need WGS84 lat/lon
zones["location_id"] = zones["LocationID"].astype(str)
zones = zones.rename(columns={"zone": "zone_name"})
zones[["location_id", "zone_name", "borough", "geometry"]].to_file(
    "dashboard/taxi_zones.geojson", driver="GeoJSON"
)
print(f"Wrote {len(zones)} zones -> dashboard/taxi_zones.geojson")