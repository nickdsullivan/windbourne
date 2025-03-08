from data_collector import DataCollector
from visualize import Visualizer
dc = DataCollector()
# dc.clear()
# dc.download_windborne_data()
# dc.clear_wind()
# lat, long = dc.get_balloon_location(1)
# windcolumn = dc.get_wind(lat, long)

# elevations = windcolumn["Elevation"].tolist()

# wind_speeds = windcolumn["Speed"]
# directions = windcolumn["Bearing"]
# visualizer.visualize_wind(elevations, wind_speeds, directions,balloon_elevation=17)
# dc.add_balloon_speed()
# dc.fill_missing_hours(0, 23)
# dc.fill_missing_data()
# dc.add_balloon_speed()
df = dc.balloon_data
visualizer = Visualizer()
visualizer.create_gif_last_24h(df, 'movie.gif')
# visualizer.visualize_wind(elevations, wind_speeds, directions,balloon_elevation=17)
# visualizer.create_gif_last_24h(df)