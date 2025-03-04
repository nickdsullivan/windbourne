import requests, json
import pandas as pd
from datetime import datetime, timedelta, timezone
import time
import numpy as np
from tools import earth_distance, convert_time_string_meteo, calculate_euclidean_distance_with_elevation, elevation_to_pressure
class DataCollector:
    def __init__(self):
        self.balloon_data       = pd.read_csv("./data/Windborne.csv")
        self.winddata       = pd.read_csv("./data/data.csv")
        self.windborne_filename = "./data/Windborne.csv"

        self.data_filename      = "./data/data.csv"
        self.number_of_balloons = 1000
        self.latest_collection_time = pd.to_datetime(self.balloon_data["Datetime"].max())
        
        self.elevations= [0.11, 0.32, 0.5, 0.8, 1.0, 1.5, 1.9, 3.0, 4.2, 5.6, 7.2, 9.2, 10.4, 11.8, 13.5, 15.8, 17.7, 19.3, 22.0]
    def download_windborne_data(self):
        current_time = datetime.now(timezone.utc).replace(tzinfo=None)
        
        
        # If we are on the last minute just wait.  I don't want to deal with it
        if current_time.minute == 59:
            print("Too close to the update point waiting a minute or two")
            time.sleep(120 - current_time.second)
            current_time = datetime.now(timezone.utc).replace(tzinfo=None)

        time = current_time.replace(minute=0, second=0, microsecond=0)
        self.latest_collection_time = time
        
        for hour in range(24):
            if hour < 10 and hour >= 0:
                url = f"https://a.windbornesystems.com/treasure/0{hour}.json"
            elif hour < 24:
                url = f"https://a.windbornesystems.com/treasure/{hour}.json"
            else:
                raise IndexError
            response = requests.get(url)
            time = time - timedelta(hours=hour)
            if response.status_code != 200:
                # If we get a non regular response we log it as bad
                
                # We know there are 1000 balloons.  It is nice this doesn't change
                for balloon in range(1000):
                    balloon_row = {
                        "Balloon": balloon,       
                        "Datetime": time, 
                        "Latitude": np.nan,
                        "Longitude": np.nan,
                        "Elevation": np.nan,
                        "Speed": np.nan,
                        "Bearing": np.nan,
                    }
                    self.balloon_data.loc[len(self.balloon_data)] = balloon_row
                continue
            # We got a regular response code.  Get the text
            raw_data = response.text
            # I noticed how you were currupting the json :)
            if raw_data[0] != "[":
                raw_data = "[" + raw_data 
            try:
                data = np.array(json.loads(raw_data))
            except:
                with open(f"../badjsons/hour_{hour}.txt", "wb") as f:
                    f.write(raw_data)    
                
            for balloon in range(data.shape[0]):
                balloon_row = {
                       "Balloon": balloon,       
                       "Datetime": time, 
                       "Latitude": data[balloon][0],
                       "Longitude": data[balloon][1],
                       "Elevation": data[balloon][2],
                       "Speed": np.nan,
                       "Bearing": np.nan,
                       }
                self.balloon_data.loc[len(self.balloon_data)]= balloon_row
        self.balloon_data = self.balloon_data.drop_duplicates()
        self.balloon_data = self.balloon_data.reset_index(drop=False)
        self.balloon_data.to_csv(self.windborne_filename,index=False)
    
        self.clear_wind()
    def add_balloon_speed(self):
        times = pd.to_datetime(self.balloon_data["Datetime"]).unique().tolist()
        for time in times:
            df = self.balloon_data[pd.to_datetime(self.balloon_data["Datetime"]) == time]
            df2 = self.balloon_data[pd.to_datetime(self.balloon_data["Datetime"]) == (time - timedelta(hours=1))]
            if len(df) == 0 or len(df2) == 0:
                continue
            for balloon_number in range(self.number_of_balloons):
                row  = df[df["Balloon"] == balloon_number]
                row2 = df2[df2["Balloon"] == balloon_number]
                loc1 = (row["Latitude"].iloc[0], row ["Longitude"].iloc[0], row["Elevation"].iloc[0])
                loc2 = (row2["Latitude"].iloc[0], row2["Longitude"].iloc[0], row2["Elevation"].iloc[0])
                balloon_speed, balloon_bearing = calculate_euclidean_distance_with_elevation(loc1,loc2)
                self.balloon_data.loc[row.index, "Speed"] = balloon_speed
                self.balloon_data.loc[row.index, "Bearing"] = balloon_bearing
        self.balloon_data.to_csv(self.windborne_filename,index=False)
    
    # Doesn't save the wind data as a csv
    def get_wind(self, lat, long, time = None) -> pd.DataFrame:
        if time == None:
            time = self.latest_collection_time
        pressures = []
        for elevation in self.elevations:
            pressures.append(elevation_to_pressure(elevation))

        df = self.get_wind_data_from_csv(lat, long, time)
        if len(df) != 0:
            return df

        speeds, bearings = self.get_meteo_data(lat, long, time, pressures)
        if speeds is None or bearings is None:
            return df
        for i in range(len(speeds)):
            new_row = {
                "Datetime": time,
                "Latitude": lat,
                "Longitude": long,
                "Elevation": self.elevations[i],
                "Pressure": pressures[i],
                "Speed": speeds[i],
                "Bearing": bearings[i]
            }
            df.loc[len(df)] = new_row

        return df  

    # saves the wind in the wind column csv and returns a new dataframe with only that dat
    def save_wind(self, lat, long, time = None) -> pd.DataFrame:
        if time == None:
            time = self.latest_collection_time
        pressures = []
        for elevation in self.elevations:
            pressures.append(elevation_to_pressure(elevation))
        df = self.winddata.iloc[0:0]
        speeds, bearings = self.get_meteo_data(lat, long, time, pressures)
        if speeds is None or bearings is None:
            return df
        for i in range(len(speeds)):
            new_row = {
                "Datetime": time,
                "Latitude": lat,
                "Longitude": long,
                "Elevation": self.elevations[i],
                "Pressure": pressures[i],
                "Speed": speeds[i],
                "Bearing": bearings[i]
            }
            self.winddata.loc[len(self.winddata)] = new_row
            df.loc[len(df)] = new_row
        self.winddata = self.winddata.drop_duplicates()   
        self.winddata.to_csv(self.data_filename, index=False)
        return df


    def get_meteo_data(self, latitude, longitude, current_time, pressures = [250]):
        url = "https://api.open-meteo.com/v1/forecast"
        data_cats = []
        for pressure in pressures:
            data_cats.append(f"wind_speed_{pressure}hPa")
            data_cats.append(f"wind_direction_{pressure}hPa")
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": data_cats,
            "hourly": data_cats,
        }
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            data = response.json()
            times = list(map(convert_time_string_meteo, data["hourly"]["time"]))
            speeds = []
            directions = []
            # print(type(current_time))
            #current_time = datetime.strptime(current_time, "%Y-%m-%d %H:%M:%S")
            for pressure in pressures:
                speeds.append(data["hourly"][f"wind_speed_{pressure}hPa"][times.index(current_time)])
                directions.append(data["hourly"][f"wind_direction_{pressure}hPa"][times.index(current_time)])
            return speeds, directions

        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            return None, None
        except ValueError as e: # Catch json decode errors
            print(f"Invalid JSON response: {e}, response text: {response.text}")
            return None, None
        


    def clear_wind(self):
        self.winddata = pd.DataFrame(columns=[ 
                        "Datetime", 
                        "Latitude",
                        "Longitude",
                        "Elevation",
                        "Pressure",
                        "Speed",
                        "Bearing",
                        ])
    def clear_balloon(self):
        self.balloon_data = pd.DataFrame(columns=[
                        "Balloon",
                        "Datetime", 
                        "Latitude",
                        "Longitude",
                        "Elevation",
                        "Speed",
                        "Bearing",
        ])  
    def clear(self):
        self.clear_balloon()
        self.clear_wind()

    def wind_data_contains(self, lat, long, time) -> bool:
        df = self.winddata[self.winddata["Datetime"].astype(str) == str(time)]
        df = df[df["Latitude"] == lat]
        df = df[df["Longitude"] == long]
        return len(df == 0)
    
    def get_wind_data_from_csv(self, lat, long, time):
        df = self.winddata[self.winddata["Datetime"].astype(str) == str(time)]

        df = df[df["Latitude"] == lat]
        df = df[df["Longitude"] == long]
        return df
    
    def get_balloon_data_at_time(self, time)-> pd.DataFrame: 
        df = self.balloon_data[self.balloon_data["Datetime"].astype(str) == str(time)]
        return df
    

    def get_balloon_location(self, number, time = None):
        if time is None:
            time = self.latest_collection_time
        df = self.get_balloon_data_at_time(time)
        
        df = df[df["Balloon"] == number]
        
        return df["Latitude"].iloc[0], df["Longitude"].iloc[0]
