import requests, json
import pandas as pd
from datetime import datetime, timedelta
import time
import numpy as np
class DataCollector:
    def __init__(self,verbose = 0):
        self.verbose = verbose
        self.ledger = pd.read_csv("./data/Ledger.csv")
        
        self.windborne_df =  pd.read_csv("./data/Windborne.csv")
        self.windborne_df =  pd.read_csv("./data/Windborne.csv")
        self.windborne_filename = "./data/Windborne.csv"

       
    def download_windborne_data(self):
        current_time = datetime.now()
        # If we are on the last minute just wait.  I don't want to deal with it
        if current_time.minute == 59:
            time.sleep(120 - current_time.second)
        
        for hour in range(24):
            if hour < 10 and hour >= 0:
                url = f"https://a.windbornesystems.com/treasure/0{hour}.json"
            elif hour < 24:
                url = f"https://a.windbornesystems.com/treasure/{hour}.json"
            else:
                raise IndexError
            response = requests.get(url)
            time = current_time.replace(minute=0, second=0, microsecond=0)
            time = time - timedelta(hours=hour)
            # Add a new row in the ledger
            new_row = {"Data Source": "Windborne", 
                       "Time": time, 
                       "Filename": self.windborne_filename,
                       "Time of Collection": datetime.now(),
                       "Missing Data": False
                       }
            if response.status_code != 200:
                # If we get a non regular response we log it as bad
                new_row["Missing Data"] = True
                self.ledger.loc[len(self.ledger)] = new_row
                

                # We know there are 1000 balloons.  It is nice this doesn't change
                for balloon in range(1000):
                    balloon_row = {
                        "Balloon": balloon,       
                        "Datetime": time, 
                        "Latitude": None,
                        "Longitude": None,
                        "Elevation": None,
                    }
                    self.windborne_df.loc[len(self.windborne_df)] = balloon_row
                if self.verbose > 2:
                    print(f"({hour}) Response Code: {response.status_code}")
                continue

            
            # We got a regular response code.  Get the text
            raw_data = response.text
            # I noticed how you were currupting the json :)
            if raw_data[0] != "[":
                raw_data = "[" + raw_data 
            try:
                data = np.array(json.loads(raw_data))
                if self.verbose > 3:
                    print(f"({hour}) Succeeded")
            except:
                if self.verbose > 1:
                    print(f"({hour}) Bad Json writing to txt")
                    with open(f"../badjsons/hour_{hour}.txt", "wb") as f:
                        f.write(raw_data)    
                new_row["Missing Data"] = True
                self.ledger.loc[len(self.ledger)] = new_row

            

            self.ledger.loc[len(self.ledger)] = new_row
            for balloon in range(data.shape[0]):
                balloon_row = {
                       "Balloon": balloon,       
                       "Datetime": time, 
                       "Id": f"{balloon} {time}", 
                       "Latitude": data[balloon][0],
                       "Longitude": data[balloon][1],
                       "Elevation": data[balloon][2],
                       }
                self.windborne_df.loc[len(self.windborne_df)]= balloon_row
        self.windborne_df.to_csv("./data/windborne.csv")
        self.ledger.to_csv("./data/Ledger.csv")

            



        

    def download_meteo_data(self, location, heights = []):
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": location[0],
            "longitude": location[1],
            "current": "temperature_2m,wind_speed_10m",
            "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m"
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            data = response.json()
            print(data)

        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
        except ValueError as e: # Catch json decode errors
            print(f"Invalid JSON response: {e}, response text: {response.text}")