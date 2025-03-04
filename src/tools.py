import math
from datetime import datetime, timedelta
import pyproj
import numpy as np
import cv2
def earth_distance(loc1,loc2):
    lat1, long1 = loc1[0] * math.pi/180, loc1[1] * math.pi/180
    lat2, long2 = loc2[0] * math.pi/180, loc2[1] * math.pi/180
    earth_radius = 6371
    delta_psi    = (loc1[0] - loc2[0]) * math.pi/180
    delta_lambda = (loc1[1] - loc2[1]) * math.pi/180
    a = math.sin(delta_psi/2) * math.sin(delta_psi/2) + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lambda/2) * math.sin(delta_lambda/2)
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return earth_radius * c



def calculate_euclidean_distance_with_elevation(loc1,loc2):
    ecef = pyproj.CRS("EPSG:4978")  # ECEF (WGS 84)
    lla = pyproj.CRS("EPSG:4326")  # Latitude/longitude (WGS 84)
    transformer = pyproj.Transformer.from_crs(lla, ecef, always_xy=True)
    lat1, long1, elev1 = loc1[0], loc1[1],loc1[2]
    lat2, long2, elev2 = loc2[0], loc2[1],loc2[2]

    x1, y1, z1 = transformer.transform(long1, lat1, elev1)
    x2, y2, z2 = transformer.transform(long2, lat2, elev2)

    distance = (math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)) / 1000
    lat1, long1 = loc1[0] * math.pi/180, loc1[1] * math.pi/180
    lat2, long2 = loc2[0] * math.pi/180, loc2[1] * math.pi/180

    delta_psi    = (loc2[0] - loc1[0]) * (math.pi/180)
    delta_lambda = math.radians(long2 / (math.pi/180) - long1 / (math.pi/180) )
    X = math.sin(delta_lambda) * math.cos(lat2)
    Y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lambda)
    angle = math.atan2(X,Y) / (math.pi/180)
    if angle < 0:
        angle = 360 + angle
    return distance, angle

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




def pin(image, location, alpha):
    color = (0, 0, 255)
    radius = 5
    thickness = -1  
    overlay = image.copy()
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


    
