from data_collector import DataCollector
from visualize import Visualizer
dc = DataCollector()
# dc.clear()
# dc.download_windborne_data()
dc.clear_wind()
lat, long = dc.get_balloon_location(1)
windcolumn = dc.get_wind(lat, long)

elevations = windcolumn["Elevation"].tolist()
wind_speeds = windcolumn["Speed"]
directions = windcolumn["Bearing"]
visualizer = Visualizer()

visualizer.visualize_wind(elevations, wind_speeds, directions,balloon_elevation=17)
