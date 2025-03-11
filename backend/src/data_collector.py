import requests, json
import pandas as pd
pd.options.mode.chained_assignment = None  # default='warn'
from datetime import datetime, timedelta, timezone
import time
import numpy as np
import math
from src.tools import earth_distance, convert_time_string_meteo, elevation_to_pressure, move_distance_to_lat_long
class DataCollector:
    def __init__(self):
        self.balloon_data       = pd.read_csv("./data/Windborne.csv")
        self.winddata       = pd.read_csv("./data/data.csv")
        self.balloon_data_filename = "./data/Windborne.csv"

        self.wind_data_filename      = "./data/data.csv"
        self.number_of_balloons = 1000
        self.latest_collection_time = pd.to_datetime(self.balloon_data["Datetime"].max())
        self.num_calls = 0
        self.elevations= [1.9, 3.0, 4.2, 5.6, 7.2, 9.2, 10.4, 11.8, 13.5, 15.8, 17.7, 19.3, 22.0]

        #self.elevations= [0.11, 0.32, 0.5, 0.8, 1.0, 1.5, 1.9, 3.0, 4.2, 5.6, 7.2, 9.2, 10.4, 11.8, 13.5, 15.8, 17.7, 19.3, 22.0]

        self.num_api_calls = 0
    def download_windborne_data(self):
        current_time = datetime.now(timezone.utc).replace(tzinfo=None)
        
        
        # If we are on the last minute just wait.  I don't want to deal with it
        time = current_time.replace(minute=0, second=0, microsecond=0)
        self.latest_collection_time = time
        time = time + timedelta(hours=1) # We have to subtract at the beginning so just add one here
        for hour in range(24):
            time = time - timedelta(hours=1)
            if hour < 10 and hour >= 0:
                url = f"https://a.windbornesystems.com/treasure/0{hour}.json"
            elif hour < 24:
                url = f"https://a.windbornesystems.com/treasure/{hour}.json"
            else:
                raise IndexError
            response = requests.get(url)
            if response.status_code != 200:
                # if hour == 0:
                #     return -1
                # print(f"({hour}) Failed")
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
                        "Hour": hour,
                    }
                    self.balloon_data.loc[len(self.balloon_data)] = balloon_row
                continue
            print(f"({hour}) Succeeded")
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
                       "Latitude": round(data[balloon][0],3),
                       "Longitude": round(data[balloon][1],3),
                       "Elevation": round(data[balloon][2],3),
                       "Speed": np.nan,
                       "Bearing": np.nan,
                       "Hour": hour,
                       }
                self.balloon_data.loc[len(self.balloon_data)]= balloon_row
        self.balloon_data = self.balloon_data.drop_duplicates()
        self.balloon_data = self.balloon_data.reset_index(drop=False)
        self.balloon_data.to_csv(self.balloon_data_filename,index=False)
        return 0
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
                balloon_speed, balloon_bearing = earth_distance(loc1,loc2)
                self.balloon_data.loc[row.index, "Speed"] = balloon_speed
                self.balloon_data.loc[row.index, "Bearing"] = balloon_bearing
        self.balloon_data.to_csv(self.balloon_data_filename,index=False)
    
    def hour2time(self, hour):
        # This is a weird function it ADDS hours to the current hour.  So If you are going into the future pass a negative hour...
        time_zero = self.balloon_data[self.balloon_data["Hour"] == 0]["Datetime"].iloc[0]
        time_zero = datetime.strptime(time_zero, "%Y-%m-%d %H:%M:%S")
        time = time_zero + timedelta(hours=hour)
        return time
    def save_balloon_data(self):
        self.balloon_data.to_csv(self.balloon_data_filename,index=False)
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
            print("No wind data found")
            return df
        for i in range(len(speeds)):
            new_row = {
                "Datetime": time,
                "Latitude": round(lat,3),
                "Longitude": round(long,3),
                "Elevation": round(self.elevations[i],3),
                "Pressure": pressures[i],
                "Speed": speeds[i],
                "Bearing": bearings[i]
            }
            df.loc[len(df)] = new_row
        return df  


   

    # saves the wind in the wind column csv and returns a new dataframe with only that dat
    def get_and_save_wind(self, lat, long, time = None) -> pd.DataFrame:
        if time == None:
            time = self.latest_collection_time
        pressures = []
        for elevation in self.elevations:
            pressures.append(elevation_to_pressure(elevation))
        df = self.get_wind_data_from_csv(lat, long, time)
        if len(df) != 0:
            return df
        df = self.winddata.iloc[0:0]
        end_time = (time + timedelta(days = 1)).strftime("%Y-%m-%d")
        start_time   = time.strftime("%Y-%m-%d")
        speeds, bearings = self.get_meteo_data(lat, long, time, pressures, start_date = start_time, end_date = end_time)
        if speeds is None or bearings is None:
            return df
        for i in range(len(speeds)):
            new_row = {
                "Datetime": time,
                "Latitude": round(lat,3),
                "Longitude": round(long,3),
                "Elevation": round(self.elevations[i],3),
                "Pressure": pressures[i],
                "Speed": speeds[i],
                "Bearing": bearings[i]
            }
            
            self.winddata.loc[len(self.winddata)] = new_row
            df.loc[len(df)] = new_row
        self.winddata = self.winddata.drop_duplicates()   
        self.winddata.to_csv(self.wind_data_filename, index=False)
        return df

    # Multi location wind
    def get_and_save_wind_multi_loc(self, locations, query_time) -> pd.DataFrame:
        start_time = query_time.strftime("%Y-%m-%d")
        end_time = (query_time + timedelta(days=1)).strftime("%Y-%m-%d")
        pressures = []
        for elevation in self.elevations:
            pressures.append(elevation_to_pressure(elevation))
        unfound_lats = []
        unfound_longs = []
        df = self.winddata.iloc[0:0]
        for location in locations:
            lat, long = location[0], location[1]
            new_data = self.get_wind_data_from_csv(lat, long, query_time)
            if len(new_data) == 0:
                unfound_lats.append(lat)
                unfound_longs.append(long)
            else:
                df = pd.concat([df, new_data])
        if len(unfound_lats) != 0:
            results = self.get_meteo_data_bulk(unfound_lats, unfound_longs, query_time, pressures, start_date=start_time, end_date=end_time)
            if results is None:
                time.sleep(60)
                results = self.get_meteo_data_bulk(unfound_lats, unfound_longs, query_time, pressures, start_date=start_time, end_date=end_time)
                if results is None:
                    return None
            for loc_index in range(len(results)):
                lat, long = locations[loc_index]
                speeds, bearings = results[loc_index]
                if speeds is None or bearings is None:
                    return df
                for i in range(len(speeds)):
                    new_row = {
                        "Datetime": time,
                        "Latitude": round(lat,3),
                        "Longitude": round(long,3),
                        "Elevation": round(self.elevations[i],3),
                        "Pressure": pressures[i],
                        "Speed": speeds[i],
                        "Bearing": bearings[i]
                    }
                    self.winddata.loc[len(self.winddata)] = new_row
                    df.loc[len(df)] = new_row
        self.winddata = self.winddata.drop_duplicates()   
        self.winddata.to_csv(self.wind_data_filename, index=False)
        return df



    def get_wind_data_from_csv(self, lat, long, time):
        df = self.winddata[self.winddata["Datetime"].astype(str) == str(time)]
        df = df[df["Latitude"] == lat]
        df = df[df["Longitude"] == long]
        return df
    
    def get_meteo_data(self, latitude, longitude, current_time, pressures = [250], start_date = None, end_date = None):

        url = "https://api.open-meteo.com/v1/forecast"
        data_cats = []
        for pressure in pressures:
            data_cats.append(f"wind_speed_{pressure}hPa")
            data_cats.append(f"wind_direction_{pressure}hPa")
        params = {
            "latitude": float(latitude),
            "longitude": float(longitude),
            "hourly": data_cats,
        }
        if not start_date is None and not end_date is None:
            params["start_date"] = start_date
            params["end_date"]   = end_date
        else:
            params["current"]    = data_cats,
        
        try:
            response = requests.get(url, params=params)
            self.num_api_calls += 1
            
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            data = response.json()
            times = list(map(convert_time_string_meteo, data["hourly"]["time"]))
            speeds = []
            directions = []

            for pressure in pressures:
                speeds.append(data["hourly"][f"wind_speed_{pressure}hPa"][times.index(current_time)])
                directions.append(data["hourly"][f"wind_direction_{pressure}hPa"][times.index(current_time)])
            return speeds, directions

        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {print(params)}")
            print(e)
            print(f"{url}")
            return None, None
        except ValueError as e: # Catch json decode errors
            print(f"Invalid JSON response: {e}, response text: {response.text}")
            return None, None
        
    def get_meteo_data_bulk(self, latitude: list, longitude: list, query_time, pressures = [250], start_date = None, end_date = None):
        url = "https://api.open-meteo.com/v1/forecast"
        data_cats = []
        for pressure in pressures:
            data_cats.append(f"wind_speed_{pressure}hPa")
            data_cats.append(f"wind_direction_{pressure}hPa")
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": data_cats,
        }
        if not start_date is None and not end_date is None:
            params["start_date"] = start_date
            params["end_date"]   = end_date
        else:
            params["current"]    = data_cats,
        
        try:
            response = requests.get(url, params=params)
            self.num_api_calls += len(latitude)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            data = response.json()
            results = []
            for location in data:
                speeds = []
                directions = []
                times = list(map(convert_time_string_meteo, location["hourly"]["time"]))
                for pressure in pressures:
                    speeds.append(location["hourly"][f"wind_speed_{pressure}hPa"][times.index(query_time)])
                    directions.append(location["hourly"][f"wind_direction_{pressure}hPa"][times.index(query_time)])
                results.append((speeds,directions))
            return results

        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {print(params)}")
            print(e)
            return None, None
        except ValueError as e: # Catch json decode errors
            print(f"Invalid JSON response: {e}, response text: {response.text}")
            return None, None
    def clear_wind(self):
        self.winddata   = pd.DataFrame(columns=[ 
                        "Datetime", 
                        "Latitude",
                        "Longitude",
                        "Elevation",
                        "Pressure",
                        "Speed",
                        "Bearing",
                        ])
        self.winddata.to_csv(self.wind_data_filename, index=False)
    def clear_balloon(self):
        self.balloon_data = pd.DataFrame(columns=[
                        "Balloon",
                        "Datetime", 
                        "Latitude",
                        "Longitude",
                        "Elevation",
                        "Speed",
                        "Bearing",
                        "Hour",
        ])  
        self.balloon_data.to_csv(self.balloon_data_filename, index=False)
    def clear(self):
        self.clear_balloon()
        self.clear_wind()

    def wind_data_contains(self, lat, long, time) -> bool:
        df = self.winddata[self.winddata["Datetime"].astype(str) == str(time)]
        df = df[df["Latitude"] == lat]
        df = df[df["Longitude"] == long]
        return len(df == 0)
    
   
    
    def get_balloon_data_at_time(self, time)-> pd.DataFrame: 
        df = self.balloon_data[self.balloon_data["Datetime"].astype(str) == str(time)]
        return df
    
    def get_balloon_location(self, number, hour = 0):
        df = self.balloon_data
        df = df[df["Hour"] == hour]
        df = df[df["Balloon"] == number]
        return df["Latitude"].iloc[0], df["Longitude"].iloc[0], df["Elevation"].iloc[0]

        
    def get_balloon_details(self, number, hour = 0):
        df = self.balloon_data
        df = df[df["Hour"] == hour]
        df = df[df["Balloon"] == number]
        return df["Latitude"].iloc[0], df["Longitude"].iloc[0], df["Elevation"].iloc[0], df["Speed"].iloc[0], df["Bearing"].iloc[0]


    def get_balloon_details_as_json(self, number, hour = 0):
        df = self.balloon_data
        df = df[df["Hour"] == hour]
        df = df[df["Balloon"] == number]
        return {"lat" : df["Latitude"].iloc[0], "long" : df["Longitude"].iloc[0], "alt":  df["Elevation"].iloc[0], "speed": df["Speed"].iloc[0], "bearing": df["Bearing"].iloc[0], "hour": df["Hour"].iloc[0]}

    def hour_unavailable(self,hour):
        return self.balloon_data[self.balloon_data["Hour"] == hour]["Latitude"].isna().all()

    def exterpolate_left(self, hour):
        df = self.balloon_data[self.balloon_data["Hour"] == hour + 1]
        idx = self.balloon_data[self.balloon_data["Hour"] == hour].index
        if len(df) == 0:
            raise IndexError ("Hour too far")

        # reverse the speed and bearing
        
        if len(df["Speed"].to_numpy()) == 0:
            speed = np.random.choice([0, 120], size=1000)
        if len(df["Speed"].to_numpy()) == 0:
            bearing = np.random.choice([0, 360], size=1000)
        speed = (df["Speed"].to_numpy() * -1)
        bearing = (df["Bearing"].to_numpy() + 180) % 360
        lat, long = move_distance_to_lat_long(df["Latitude"].to_numpy(), df["Longitude"].to_numpy(), speed, bearing)

        self.balloon_data.loc[idx, "Latitude"]  = lat
        self.balloon_data.loc[idx, "Longitude"] = long
        self.balloon_data.loc[idx, "Elevation"] = df["Elevation"].values
        self.balloon_data.loc[idx, "Speed"]     = speed
        self.balloon_data.loc[idx, "Bearing"]   = bearing


    def exterpolate_right(self, hour):
        df = self.balloon_data[self.balloon_data["Hour"] == hour - 1]
        
        if len(df) == 0:
            raise IndexError ("Hour too far")

        # reverse the speed and bearing
        if len(df["Speed"].to_numpy()) == 0:
            speed = np.random.choice([0, 120], size=1000)
        if len(df["Speed"].to_numpy()) == 0:
            bearing = np.random.choice([0, 360], size=1000)
        speed = df["Speed"].to_numpy()
        bearing = df["Bearing"].to_numpy()

        lat, long = move_distance_to_lat_long(df["Latitude"].to_numpy(), df["Longitude"].to_numpy(), speed, bearing)
        
        idx = self.balloon_data[self.balloon_data["Hour"] == hour].index
        self.balloon_data.loc[idx, "Latitude"]  = lat
        self.balloon_data.loc[idx, "Longitude"] = long
        self.balloon_data.loc[idx, "Elevation"] = df["Elevation"].values
        self.balloon_data.loc[idx, "Speed"]     = speed
        self.balloon_data.loc[idx, "Bearing"]   = bearing
        
    
        
    def interpolate(self, hour, starting_hour, ending_hour):
        starting_df = self.balloon_data[self.balloon_data["Hour"] == starting_hour]
        ending_df = self.balloon_data[self.balloon_data["Hour"] == ending_hour]
        df = self.balloon_data[self.balloon_data["Hour"] == hour]
        idx = self.balloon_data[self.balloon_data["Hour"] == hour].index
        difference = starting_hour - ending_hour
        if len(df) == 0:
            raise IndexError ("Hour too far")


        starting_location = (starting_df["Latitude"].to_numpy(), starting_df["Longitude"].to_numpy())
        ending_location   = (ending_df["Latitude"].to_numpy(), ending_df["Longitude"].to_numpy())
        # reverse the speed and bearing
        distances, bearing = earth_distance(starting_location, ending_location)
        distances = distances / difference
        lat, long = move_distance_to_lat_long(starting_df["Latitude"].to_numpy(), starting_df["Longitude"].to_numpy(), distances, bearing)
        elevations = starting_df["Elevation"].to_numpy() + (ending_df["Elevation"].to_numpy()-starting_df["Elevation"].to_numpy()) / difference
        self.balloon_data.loc[idx, "Latitude"]  = lat
        self.balloon_data.loc[idx, "Longitude"] = long
        self.balloon_data.loc[idx, "Elevation"] = elevations
        self.balloon_data.loc[idx, "Speed"]     = distances
        self.balloon_data.loc[idx, "Bearing"]   = bearing
        

    def fill_missing_hours(self, start_hour = 0, end_hour = 23):
        # Left exterpolation
        for hour in range(start_hour, end_hour+1, 1):
            if self.hour_unavailable(hour):
                continue
            else:
                for next_hour_left in range(hour, start_hour, -1):
                    self.exterpolate_left(next_hour_left)
                    self.add_balloon_speed()
                break
       
        for hour in range(end_hour, start_hour, -1):
            if self.hour_unavailable(hour):
                continue
            else:
                for next_hour_right in range(hour, end_hour+1, 1):
                    self.exterpolate_right(next_hour_right)
                    self.add_balloon_speed()
                break
                
        for hour in range(start_hour, end_hour+1):
            if self.hour_unavailable(hour):
                # find the largest filled in hour
                for starting_hour in range(hour, end_hour+1):
                    if self.hour_unavailable(starting_hour):
                        continue
                    else:
                        self.interpolate(hour, starting_hour=starting_hour, ending_hour=hour-1)
                        self.add_balloon_speed()
        self.save_balloon_data()

                
        



    def fill_missing_hours2(self, start_hour, end_hour):
        left = start_hour
        right  = start_hour + 1
        start_flag = False
        df = self.balloon_data
        while left != end_hour:
            if right >= end_hour:
                    right_data = df[df["Hour"] == right]
                    left_data = df[df["Hour"] == left]
                    right_data = right_data.reset_index(drop=True)
                    left_data = left_data.reset_index(drop=True)
                    idx = df[df["Hour"] == left + 1].index
                    assert len(idx) != 0, "No data for day requested"

                    loc1 = left_data["Latitude"].to_numpy(), left_data["Longitude"].to_numpy(),left_data["Elevation"].to_numpy()
                    lat, long = move_distance_to_lat_long(left_data["Latitude"].to_numpy(), left_data["Longitude"].to_numpy(), left_data["Speed"].to_numpy(), left_data["Bearing"].to_numpy())
                    loc2 = lat, long, left_data["Elevation"].to_numpy()

                    speed, bearing = earth_distance(loc1,loc2)

                    df.loc[idx, "Latitude"]  = loc2[0]
                    df.loc[idx, "Longitude"] = loc2[1]
                    df.loc[idx, "Elevation"] = left_data["Elevation"].values
                    df.loc[idx, "Speed"]     = speed
                    df.loc[idx, "Bearing"]   = bearing


                    left = left + 1
                    continue
                
            if df[df["Hour"] == right]["Latitude"].isna().all():
                if right == start_hour:
                    start_flag = True
                right = right + 1
                continue
            else:
                difference = right - left
                if difference < 2:
                    
                    right = right + 1
                    left = left + 1
                else:
                    
                    # Since left != right then we moved left and we interpolate the middle ones
                    left_data = df[df["Hour"] == left]
                    right_data = df[df["Hour"] == right]
                    right_data = right_data.reset_index(drop=True)
                    left_data = left_data.reset_index(drop=True)

                   
                    if start_flag:
                        idx = df[df["Hour"] == left].index


                        loc1 = right_data["Latitude"].to_numpy(), right_data["Longitude"].to_numpy(),  right_data["Elevation"].to_numpy()
                        lat, long = move_distance_to_lat_long(right_data["Latitude"].to_numpy(), right_data["Longitude"].to_numpy(), right_data["Speed"].to_numpy(), right_data["Bearing"].to_numpy())
                        loc2 = lat, long, right_data["Elevation"].to_numpy()
                        speed, bearing = earth_distance(loc1,loc2)

                        df.loc[idx, "Longitude"] = loc2[0]
                        df.loc[idx, "Latitude"]  = loc2[1]
                        df.loc[idx, "Elevation"] = right_data["Elevation"].values
                        df.loc[idx, "Speed"]     = speed
                        df.loc[idx, "Bearing"]   = bearing
                        left = left + 1
                       
                    else: 

                        idx = df[df["Hour"] == left + 1].index
                        


                        lat  = left_data["Latitude"].values +  (right_data["Latitude"].values  - left_data["Latitude"].values )/difference
                        long = left_data["Longitude"].values + (right_data["Longitude"].values - left_data["Longitude"].values)/difference
                        alt  = left_data["Elevation"].values + (right_data["Elevation"].values - left_data["Elevation"].values)/difference


                        loc1 = left_data["Latitude"].to_numpy(), left_data["Longitude"].to_numpy(), left_data["Elevation"].to_numpy()
                        loc2 = lat, long, alt
                        df.loc[idx, "Latitude"]  = lat
                        df.loc[idx, "Longitude"] = long
                        df.loc[idx, "Elevation"] = alt
                        speed, bearing = earth_distance(loc1, loc2)
                        df.loc[idx, "Speed"]   = speed
                        df.loc[idx, "Bearing"] = bearing



                        # we also calculate the right side speed!

                        loc1 = lat, long, alt
                        loc2 = right_data["Latitude"].to_numpy(), right_data["Latitude"].to_numpy(),  right_data["Elevation"].to_numpy()
                        speed, bearing = earth_distance(loc1, loc2)
                        idx = df[df["Hour"] == right].index
                        df.loc[idx, "Speed"]   = speed
                        df.loc[idx, "Bearing"] = bearing

                        left = left + 1
                        
                    
        self.balloon_data = df
        self.add_balloon_speed()
        self.save_balloon_data()
        
    
    def fill_missing_data(self):

            df = self.balloon_data
            lat_indices  =  df[df["Latitude"].isna()].index
            long_indices =  df[df["Longitude"].isna()].index
            alt_indices  =  df[df["Elevation"].isna()].index
            self.find_values(df, lat_indices, "Latitude")
            self.find_values(df, long_indices, "Longitude")
            self.find_values(df, alt_indices, "Elevation")
            self.add_balloon_speed()
            self.save_balloon_data()

    def find_values(self,df, indices, column):
        df = df.loc[indices]
        for index in df.index:
            row = df.loc[index]
            balloons = self.balloon_data[self.balloon_data["Balloon"] == row["Balloon"]]
            hour = row["Hour"]
            left = hour - 1
            right = hour + 1
            while left >= 0 or right <= df["Hour"].max():
                # Edge case most recent
                if left < 0 and right <= df["Hour"].max():
                    right_val = float('nan')

                    if len(balloons[balloons["Hour"] == right][column]) != 0:
                        right_val = balloons[balloons["Hour"] == right][column].iloc[0]

                    # If right latitude exists
                    if not np.isnan(right_val):
                        # If the next latitude is good then we hopefully have a full row and we estimate with 
                        right_data = balloons[balloons["Hour"] == right]
                        right_data = right_data.reset_index(drop=True)
                        lat, long = move_distance_to_lat_long(right_data["Latitude"].values, right_data["Longitude"].values, right_data["Speed"].values, right_data["Bearing"].values)
                        if column == "Latitude":
                            self.balloon_data.loc[index, column] =  lat
                        if column == "Longitude":
                            self.balloon_data.loc[index, column] =  long
                        if column == "Elevation":
                            self.balloon_data.loc[index, column] =  right_data["Elevation"].values
                        
                        break
                    else:
                        right = right + 1
                        continue
                # Edgecase back in time
                if right > df["Hour"].max() and left >= 0:
                    left_val = float('nan')
                    if len(balloons[balloons["Hour"] == left][column]) != 0:
                        left_val = balloons[balloons["Hour"] == left][column ].iloc[0]

                    # if the left lat exists
                    if not np.isnan(left_val):
                        left_data = balloons[balloons["Hour"] == left]
                        left_data = left_data.reset_index(drop=True)

                        lat, long = move_distance_to_lat_long(left_data["Latitude"].values, left_data["Longitude"].values, left_data["Speed"].values, left_data["Bearing"].values)

                        if column == "Latitude":
                            self.balloon_data.loc[index, column] = lat
                        if column == "Longitude":
                            self.balloon_data.loc[index, column] = long
                        if column == "Elevation":
                            self.balloon_data.loc[index, column] = right_data["Elevation"].values
                        break
                    else:
                        left = left - 1
                        continue

                # Find the values around it and estimate it 
                if left >= 0 and right <= df["Hour"].max():
                    left_val = float('nan') 
                    right_val = float('nan')
                    if len(balloons[balloons["Hour"] == left][column ]) != 0:
                        left_val  = balloons[balloons["Hour"] == left][column ].iloc[0]
                    if len(balloons[balloons["Hour"] == right][column]) != 0:
                        right_val = balloons[balloons["Hour"] == right][column].iloc[0]

                    # If they exist
                    if not np.isnan(left_val) and not np.isnan(right_val):
                        self.balloon_data.loc[index, column] =  left_val + (right_val - left_val)/(right_val-left_val)
                        
                        break
                    
                    else:
                        left  = left  - 1
                        right = right + 1
            