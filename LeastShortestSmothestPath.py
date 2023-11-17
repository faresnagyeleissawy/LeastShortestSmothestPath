import streamlit as st
import geopandas as gpd
import leafmap.foliumap as lm
import leafmap.leafmap as lf
import leafmap.kepler as kp
import requests
import pandas as pd
from shapely.geometry import LineString, Point
import rasterio
import numpy as np
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from skimage.graph import route_through_array
from math import sqrt
from shapely.ops import linemerge, unary_union

#=================================var==============================================#
#     startCoord = (33.26444075788752, 30.480550154320991)
#     stopCoord = (33.629665637860086, 30.633987825788754 )
api_key = "8a07d886a504428a8e1202226231003"
base_url = "http://api.weatherapi.com/v1/current.json?key=" + api_key + "&q="
forecast_url = "http://api.weatherapi.com/v1/future.json?key=" + api_key + "&q=&dt=2023-04-09"
CostSurfacefn = 'NS.tif'
#===========================implement kepler 3d map====================================#

m = kp.Map(center=[30.5464,33.41], zoom=6, height=1000)
gdf_polygon = gpd.read_file('boundry.geojson')
gdf_polygon['geometry_type'] = 'plygon'

# ============return weather geocoding data for cities daily updates====================#
def getLocationWeather(city):
    url = base_url + city
    response = requests.get(url)
    weather_data = response.json()

    country = weather_data["location"]["country"]
    lat = weather_data["location"]["lat"]
    lon = weather_data["location"]["lon"]
    localtime = weather_data["location"]["localtime"]
    temp = weather_data["current"]["temp_c"]
    text = weather_data["current"]["condition"]["text"]
    humidity = weather_data["current"]["humidity"]
    pressure_mb = weather_data["current"]["pressure_mb"]

    df = pd.DataFrame({
        "Country": [country],
        "Temperature (°C)": [temp],
        "Humidity (%)": [humidity],
        "Pressure (mb)": [pressure_mb],
        "Weather Condition": [text],
        "Local Time": [localtime],
        "Latitude": [lat],
        "Longitude": [lon],
    })
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.Longitude, df.Latitude))
    gdf = gdf.set_crs("EPSG:4326")
    m.add_gdf(gdf)

# ======================Least distance path based on DIM and slopes Algorithm ===========#
sqrt2 = sqrt(2)
#--------------------- Read dim data and return array of band 1 -------------------------
def raster2array(rasterfn):
    with rasterio.open(rasterfn) as src:
        array = src.read(1)
    return array
#--------------------- Tranform lat long corrdinates into pixel indexs ------------------
def coord2pixelOffset(rasterfn, x, y):
    with rasterio.open(rasterfn) as src:
        transform = src.transform
        col, row = ~transform * (x, y)
        return int(col), int(row)
#------------------ Create path based on distance and slopes using route_through_array --

def createPath(CostSurfacefn, costSurfaceArray, startCoord, stopCoord):
    startCoordX, startCoordY = startCoord
    startIndexX, startIndexY = coord2pixelOffset(CostSurfacefn, startCoordX, startCoordY)

    stopCoordX, stopCoordY = stopCoord
    stopIndexX, stopIndexY = coord2pixelOffset(CostSurfacefn, stopCoordX, stopCoordY)

    
    indices, weight = route_through_array(costSurfaceArray, (startIndexY,startIndexX), (stopIndexY,stopIndexX),geometric=True,fully_connected=True)
    indices = np.array(indices).T
    path = np.zeros_like(costSurfaceArray)

    path[indices[0], indices[1]] = 1
    
    return path
#------------------ Create array of points from pixels ----------------------------------
def path2array(rasterfn, array):
    with rasterio.open(rasterfn) as src:
        transform = src.transform
        originX = transform[2]
        originY = transform[5] + transform[3]  # considering the y-axis flips
        pixelWidth = transform[0]
        pixelHeight = transform[4]
        cols = array.shape[1]
        rows = array.shape[0]

        path_data = {
            "originX": originX,
            "originY": originY,
            "pixelWidth": pixelWidth,
            "pixelHeight": pixelHeight,
            "path": []
        }

        for i in range(rows):
            for j in range(cols):
                if array[i][j] == 1:
                    x = originX + j * pixelWidth
                    y = originY + i * pixelHeight
                    path_data["path"].append({"x": x, "y": y})
    return path_data

#----------------- LeastShortestSmothestPath run algorithem and return array of points----
def  leastShortestSmothestPath(CostSurfacefn,startCoord,stopCoord):
    costSurfaceArray = raster2array(CostSurfacefn) 
    pathArray = createPath(CostSurfacefn,costSurfaceArray,startCoord,stopCoord) 
    return path2array(CostSurfacefn,pathArray)


#==================== Streamlit and handel path into the map===============================#

# -----------Split the text Convert to numbers and remove empty strings--------------------
def extractNumbers(text):
    numbers = text.split(',')  
    numbers = [float(num.strip()) for num in numbers if num.strip()]  
    return numbers
def xy2points(startCoords,stopCoords):
    
    point_buffer = Point(stopCoords[0], stopCoords[1]).buffer(0.005)
    buffer = gpd.GeoDataFrame(geometry=[point_buffer])
    buffer['geometry_type'] = 'polygon'
    points = [startCoords,stopCoords]
    points_gdf = gpd.GeoDataFrame(geometry=[Point(point[0], point[1]) for point in points])
    points_gdf['geometry_type'] = 'point'
    combined_gdf = gpd.GeoDataFrame(pd.concat([points_gdf,gdf_polygon], ignore_index=True))
    m.add_gdf(combined_gdf) 
    intersects = []
    for point in points_gdf.geometry:
        intersects.append(gdf_polygon.geometry.intersects(point))  
    all_intersects = all(s.iloc[0] for s in intersects)
    return all_intersects, points_gdf
# ----------------Create a LineString geometry from the points add to map------------------
def array2line(startCoords,stopCoords,CostSurfacefn,buffer_dis):
    startCoord =(startCoords[0],startCoords[1])
    stopCoord = (stopCoords[0],stopCoords[1])
    all_intersects, points_gdf = xy2points(startCoords,stopCoords)

    if  all_intersects:
            data= leastShortestSmothestPath(CostSurfacefn,startCoord,stopCoord)
            points = data['path']
            line = LineString([(point['x'], point['y']) for point in points])
            densified_line = line.parallel_offset(0.0015, 'left') 
            line_gdf = gpd.GeoDataFrame(geometry=[ densified_line ])
            gdf = line_gdf.set_crs("EPSG:4326")
            ax = gdf.plot(marker='o', color='red', figsize=(8, 8))  
            line_gdf.plot(ax=ax, color='Red') 
            line_gdf['geometry_type'] = 'line'
            if buffer_dis:
                point_buffer = Point(stopCoords[0], stopCoords[1]).buffer(buffer_dis)
                buffer = gpd.GeoDataFrame(geometry=[point_buffer])
                buffer['geometry_type'] = 'polygon'
                result = gpd.overlay(line_gdf,buffer, how='difference')
                gdf = result.set_crs("EPSG:4326")
                ax = gdf.plot(marker='o', color='red', figsize=(8, 8))  
                result.plot(ax=ax, color='Red') 
                result['geometry_type'] = 'line'
                combined_gdf = gpd.GeoDataFrame(pd.concat([points_gdf,result,buffer], ignore_index=True))
                m.add_gdf(combined_gdf) 
            else:
                combined_gdf = gpd.GeoDataFrame(pd.concat([points_gdf,line_gdf], ignore_index=True))
                m.add_gdf(combined_gdf) 
    else:
        "Not all points intersect with the interest area."


#----------------- streamlit inputes -------------------------------------------------------
with st.sidebar:
    st.markdown("<h1 style='color: balck; text-align: center;'>Least Shortest Smoothest Path</h1>", unsafe_allow_html=True)
    city = st.text_input("City name:")
    if city:
        getLocationWeather(city)
    startCoords = extractNumbers(st.text_input("Start Point X,Y "))
    stopCoords = extractNumbers(st.text_input("End Point X,Y "))
    startCoords =(33.26444075788752, 30.480550154320991)
    stopCoords = (33.629665637860086, 30.633987825788754)
    buffer_dis = st.number_input(('Distanc KM'))/111.32  
    if startCoords and stopCoords:
            if st.button('Generate Line'):
                  array2line(startCoords,stopCoords,CostSurfacefn,buffer_dis)
m.to_streamlit(width=100, height=550)

