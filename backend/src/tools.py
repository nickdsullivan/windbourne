import math
from datetime import datetime, timedelta
import pyproj
import numpy as np
import cv2
import os
def earth_distance(loc1,loc2):
    lat1, long1 = loc1[0] * np.pi/180, loc1[1] * np.pi/180
    lat2, long2 = loc2[0] * np.pi/180, loc2[1] * np.pi/180
    earth_radius = 6371
    delta_psi    = (loc1[0] - loc2[0]) * np.pi/180
    delta_lambda = (loc1[1] - loc2[1]) * np.pi/180
    a = np.sin(delta_psi/2) * np.sin(delta_psi/2) + np.cos(lat1) * np.cos(lat2) * np.sin(delta_lambda/2) * np.sin(delta_lambda/2)
    
    c = 2 * np.arctan2(np.pow(a, .5), np.pow(1-a, .5))
    distance = earth_radius * c

    delta_psi    = (loc2[0] - loc1[0]) * (np.pi/180)
    delta_lambda = np.deg2rad(long2 / (np.pi/180) - long1 / (np.pi/180) )
    X = np.sin(delta_lambda) * np.cos(lat2)
    Y = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(delta_lambda)
    angle = np.arctan2(X,Y) / (np.pi/180)
    angle = np.where(angle < 0, 360 + angle, angle)
    return distance, angle



def move_distance_to_lat_long(lat, lon, distance_km, bearing):
    R = 6371 

    lat = np.deg2rad(lat)
    lon = np.deg2rad(lon)
    bearing = np.deg2rad(bearing)
    new_lat = np.arcsin(np.sin(lat) * np.cos(distance_km / R) + np.cos(lat) * np.sin(distance_km / R) * np.cos(bearing))

    new_lon = lon + np.arctan2(np.sin(bearing) * np.sin(distance_km / R) * np.cos(lat), np.cos(distance_km / R) - np.sin(lat) * np.sin(new_lat))
    new_lat = np.rad2deg(new_lat)
    new_lon = np.rad2deg(new_lon)
    return new_lat, new_lon




def convert_time_string_meteo(time_str):
    gmt_time_str = time_str
    gmt_time = datetime.strptime(gmt_time_str, "%Y-%m-%dT%H:%M")
    return gmt_time



def pressure_to_elevation(pressure):
    elevation_2_pressure = {
        .110: 1000, .320 : 975, .5 :950, 0.8: 925, 
        1: 900, 1.5: 850, 1.9: 800,
        3: 700, 4.2:600, 5.6: 500, 7.2 : 400, 9.2: 300, 
        10.4: 250, 11.8: 200, 13.5: 150, 15.8: 100, 17.7: 70,
        19.3: 50, 22: 30
    }
    pressure_2_elevation = {v: k for k, v in elevation_2_pressure.iteritems()}
    pressures = np.array(list(pressure_2_elevation.keys()))
    
    differences = np.abs(pressures - pressure)
    index = np.argmin(differences)
    return elevation_2_pressure[pressures[index]]
    
    

    # converts a given elevation to pressure
def elevation_to_pressure(elevation):
    elevation_2_pressure = {
        .110: 1000, .320 : 975, .5 :950, 0.8: 925, 
        1: 900, 1.5: 850, 1.9: 800,
        3: 700, 4.2:600, 5.6: 500, 7.2 : 400, 9.2: 300, 
        10.4: 250, 11.8: 200, 13.5: 150, 15.8: 100, 17.7: 70,
        19.3: 50, 22: 30
    }
    elevations = np.array(list(elevation_2_pressure.keys()))
    
    differences = np.abs(elevations - elevation)
    index = np.argmin(differences)
    return elevation_2_pressure[elevations[index]]



def pin(image, location, alpha, radius = 5, color= (0,0,0),):
    #color_value = (float(location[2]) / 22.0) * 255
    color = color
    radius = radius
    thickness = -1  
    overlay = image.copy()
    location = location[0], location[1]
    cv2.circle(overlay, location, radius, color, thickness)
    return cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0)


def loc2pixels(location, zoom):
    lat = location[0]
    long = location[1]
    lat_rad = math.radians(lat)
    map_size = 256 * 2**zoom
    x = math.floor((long + 180) / 360 * map_size)
    y = math.floor((1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * map_size)
    return x, y


def pixels2loc(x, y, zoom):
    map_size = 256 * 2**zoom
    
    long = (x / map_size) * 360 - 180
    lat_rad = math.pi - (2 * math.pi * y) / map_size
    lat = math.degrees(math.atan(math.sinh(lat_rad)))
    
    return lat, long
    

def was_file_created_last_hour(filename):
    if not os.path.exists(filename):
        return False
    creation_time = os.path.getctime(filename)
    creation_datetime = datetime.fromtimestamp(creation_time)
    now = datetime.now()
    return now - creation_datetime <= timedelta(hours=1)



def clear_folder(folder_path):
    # Set the parent directory to 'backend', since you are currently in 'backend/src/tools'
    parent_dir = os.path.abspath(os.path.join(os.getcwd(), '..'))

    # Walk through the parent directory (backend)
    for root, dirs, files in os.walk(parent_dir):
        for file in files:
            print(os.path.join(root, file))
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        if os.path.isfile(file_path):  
            os.remove(file_path)
                



# This sucks we can;
# def calculate_euclidean_distance_with_elevation(loc1,loc2):
#     ecef = pyproj.CRS("EPSG:4978")  # ECEF (WGS 84)
#     lla = pyproj.CRS("EPSG:4326")  # Latitude/longitude (WGS 84)
#     transformer = pyproj.Transformer.from_crs(lla, ecef, always_xy=True)
#     lat1, long1, elev1 = loc1[0], loc1[1], loc1[2]
#     lat2, long2, elev2 = loc2[0], loc2[1], loc2[2]

#     x1, y1, z1 = transformer.transform(long1, lat1, elev1)
#     x2, y2, z2 = transformer.transform(long2, lat2, elev2)

#     distance = (np.power((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2, .5)) / 1000
#     lat1, long1 = loc1[0] * math.pi/180, loc1[1] * math.pi/180
#     lat2, long2 = loc2[0] * math.pi/180, loc2[1] * math.pi/180

#     delta_psi    = (loc2[0] - loc1[0]) * (math.pi/180)
#     delta_lambda = np.deg2rad(long2 / (math.pi/180) - long1 / (math.pi/180) )
#     X = np.sin(delta_lambda) * np.cos(lat2)
#     Y = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(delta_lambda)
#     angle = np.arctan2(X,Y) / (math.pi/180)
#     angle = np.where(angle < 0, 360 + angle, angle)

#     return distance, angle