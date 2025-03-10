from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from src.data_collector import DataCollector
from src.visualize import Visualizer
from src.navigator import Navigator
from src.tools import was_file_created_last_hour, clear_folder, pixels2loc
import math
import datetime
dc = DataCollector()
df = dc.balloon_data
visualizer = Visualizer()



app = FastAPI()

# Allow only the frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Only this origin is allowed
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Allow only necessary HTTP methods
    allow_headers=["Content-Type", "Authorization"],  # Restrict headers for security
)


@app.get("/refresh-data")
def refresh_data():
    print(f"{datetime.datetime.now().strftime("%m/%d %H:%M:%S")} refresh-data ()")
    clear_folder("./images")
    clear_folder("./wind_column")
    dc.clear()
    return_code = dc.download_windborne_data()
    if return_code == -1:
        dc.download_windborne_data()
    dc.add_balloon_speed()
    dc.fill_missing_hours(0, 23)
    return {"Status": "ok"}



@app.get("/balloon-map")
def get_balloon_map(hour=0):
    print(f"{datetime.datetime.now().strftime("%m/%d %H:%M:%S")} balloon-map (hour = {hour})")
    hour = int(hour)
    filename = f"images/current_positions_{hour}.png" 
    if not was_file_created_last_hour(filename):
        visualizer.create_current_map(df,hour)
    if os.path.exists(filename):
        return FileResponse(filename, media_type="image/png")
    else:
        return {"error": "Image not found"}
    



@app.get("/wind-column")
def get_balloon_map(balloon_id, hour=0):
    print(f"{datetime.datetime.now().strftime("%m/%d %H:%M:%S")} wind-column (ballon_id = {balloon_id}, hour = {hour})")
    hour = int(hour)
    balloon_id = int(balloon_id)
    lat, long, elevation = dc.get_balloon_location(balloon_id, hour)
    windcolumn = dc.get_wind(lat, long)
    elevations = windcolumn["Elevation"].tolist()
    wind_speeds = windcolumn["Speed"]
    directions = windcolumn["Bearing"]
    filename = f"wind_column/windcolumn{balloon_id}_{hour}.gif"
    try:
        if not was_file_created_last_hour(filename):
            visualizer.visualize_wind(elevations, wind_speeds, directions, balloon_elevation=elevation, filename=filename, balloon_number=balloon_id, hour=hour)
    except ValueError as e:
        print("Failed to get wind column")
    if os.path.exists(filename):
        response = FileResponse(filename, media_type="image/gif")
        response.headers["Access-Control-Allow-Origin"] = "cross-origin" 
        response.headers["Access-Control-Allow-Methods"] = "GET"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        print(f"wind-column balloon_id:{balloon_id}, hour:{hour}")
        return response
    else:
        return {"error": "Image not found"}





@app.get("/get-positions")
def get_positions(hour=0):
    print(f"{datetime.datetime.now().strftime("%m/%d %H:%M:%S")} get-positions (hour = {hour})")
    hour = int(hour)
    return JSONResponse(content= visualizer.get_positions(df,hour))



@app.get("/get-refresh-time")
def get_refresh_time():
    print(f"{datetime.datetime.now().strftime("%m/%d %H:%M:%S")} get-refresh-time ()")
    return {"time_utc" : dc.latest_collection_time}
    

@app.get("/balloon-details")
def get_balloon_details(balloon_id, hour = 0):
    print(f"{datetime.datetime.now().strftime("%m/%d %H:%M:%S")} balloon-details (ballon_id = {balloon_id}, hour = {hour})")

    balloon_id = int(balloon_id)
    hour = int(hour)
    return JSONResponse(content= dc.get_balloon_details_as_json(balloon_id,hour))
    

@app.get("/single-balloon-map-navigator")
def single_balloon_map_navigator(balloon_id, hour = 0, x = -1, y = -1):
    print(f"{datetime.datetime.now().strftime("%m/%d %H:%M:%S")} single-balloon-map-navigator (ballon_id = {balloon_id}, hour = {hour}, x = {x}, y = {y})")
    balloon_id = int(balloon_id)
    hour = int(hour)
    filename = f"images/single_{balloon_id}_{hour}.png"
    lat, long, elevation, = dc.get_balloon_location(balloon_id)
    result = visualizer.create_single_balloon_map(lat, long, elevation, filename, image = None)
    try:
        target_lat, target_long = float(x) , float(y)
    except:
        target_lat, target_long = -1, -1
    if target_lat != -1 and target_long != -1:
        visualizer.create_single_balloon_map(target_lat, target_long, elevation, filename, image = result, color = (0,0,255))

    
    if os.path.exists(filename):
        return FileResponse(filename, media_type="image/png")
    else:
        return {"error": "Image not found"}


last_node = None

@app.get("/start-navigation")

def start_navigation(lat, long, alt, t_lat, t_long, t_alt, max_iters = 20, beamWidth = 3):
    print(f"{datetime.datetime.now().strftime("%m/%d %H:%M:%S")} start-navigation (lat = {lat}, long = {long}, alt = {alt}, t_lat = {t_lat}, t_long = {t_long}, max_iters = {max_iters}, beamWidth = {beamWidth})")

    navigator = Navigator()
    max_iters = max(min(int(max_iters),100),1)
    beamWidth = max(min(int(beamWidth),20),1)
    lat = float(lat)
    long = float(long)
    alt = float(alt)
    t_lat = float(t_lat)
    t_long = float(t_long)
    t_alt = float(t_alt)
    
    navigator.set_values((lat, long, alt), (t_lat, t_long, t_alt), tolerance= 10, beam_width=10)
    last_node = navigator.beam_search(max_iters)
    create_path_map(lat, long, alt, t_lat, t_long, t_alt, last_node, navigator=navigator)
    return JSONResponse(content = navigator.get_path_json(last_node))





def create_path_map(lat, long, alt, t_lat, t_long, t_alt, last_node, navigator):
    filename = f"images/current_path.png"
    result = visualizer.create_single_balloon_map(lat, long, alt, filename, image = None)
    
    if not last_node is None:
        nodes = navigator.get_path_json(last_node)
        for node in nodes:
            result = visualizer.create_single_balloon_map(node["lat"], node["long"], node["alt"], filename, image = result, color = (255,0,0),radius=2, alpha=1)
    result = visualizer.create_single_balloon_map(t_lat, t_long, t_alt, filename, image = result, color = (0,0,255))
    visualizer.create_single_balloon_map(lat, long, alt, filename, image = result)
    




@app.get("/get-directions-map")
def get_directions_map(balloon_id, hour = 0):
    print(f"{datetime.datetime.now().strftime("%m/%d %H:%M:%S")} balloon-details (ballon_id = {balloon_id}, hour = {hour})")

    balloon_id = int(balloon_id)
    hour = int(hour)
    filename = f"images/current_path.png"
    if os.path.exists(filename):
        return FileResponse(filename, media_type="image/png")
    else:
        return {"error": "Image not found"}


