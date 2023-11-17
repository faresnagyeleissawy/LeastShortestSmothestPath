Least Shortest Smoothest Path
This application calculates the least, shortest, and smoothest path between two points while incorporating geospatial data and weather information.

Features
Weather Data: Provides current weather information for a specified city.
Path Calculation: Utilizes Digital Elevation Model (DEM) and slope data to generate the least, shortest, and smoothest path between specified start and end points.
Interactive Map Visualization: Displays the path on an interactive map powered by Kepler.gl, Leafmap, and GeoPandas.
Dependencies
Ensure you have the following Python packages installed:

Streamlit
Geopandas
Leafmap
Requests
Rasterio
Numpy
Scikit-image
Shapely
Usage

Launch the App: Run the Streamlit app in your local environment using streamlit run app.py.
Input City and Coordinates: Enter the city name, start point (X,Y), and end point (X,Y) in the sidebar.
Generate Path: Click the "Generate Line" button to calculate and visualize the path.

This project utilizes various Python libraries for geospatial data manipulation and visualization.
Weather data is obtained through the WeatherAPI service.
DEM data is used for path calculation.
