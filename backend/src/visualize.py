from src.tools import pin, loc2pixels
import math
import cv2
import pandas as pd
import numpy as np
import imageio
import re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.patches import FancyArrowPatch
from mpl_toolkits.mplot3d import proj3d
from matplotlib.animation import FuncAnimation

from mpl_toolkits.mplot3d.art3d import Line3D
from datetime import timedelta


class Visualizer:
    def __init__(self):
        self.balloon_data = pd.read_csv("./data/Windborne.csv")
        self.winddata     = pd.read_csv("./data/data.csv")
        self.image_folder = "images/"
        self.base_map = "map.jpg"

    
    def create_gif_last_24h(self, df, filename):  
        image = cv2.imread(self.base_map)
        result = image.copy()
        filenames = []
        for hour in range(24):
            if hour == 0:
                lats        = df[df["Hour"] == hour]["Latitude"].to_list()
                longs       = df[df["Hour"] == hour]["Longitude"].to_list()
                elevations  = df[df["Hour"] == hour]["Elevation"].to_list()
                result = self.create_map(result, lats, longs, elevations, 1, "gif/current_positions.png", save = True)
            
            result = image.copy()
            name = str(24-hour) + ".png"
            filename = self.image_folder + name
            filenames.append(filename)


            for ghost_hours in range(max(0,hour-2), hour+1):
                lats        = df[df["Hour"] == ghost_hours]["Latitude"].to_list()
                longs       = df[df["Hour"] == ghost_hours]["Longitude"].to_list()
                elevations  = df[df["Hour"] == ghost_hours]["Elevation"].to_list()
                alpha = math.exp(-1*(hour-ghost_hours))
                result = self.create_map(result, lats, longs, elevations, alpha, name, save = False)
            cv2.imwrite(f"{self.image_folder}{name}", result) 
                
        

        images = []
        filenames.sort(key=lambda x: int(re.search(r"\d+", x).group()))
        for filename in filenames:
            images.append(imageio.imread(filename))

        imageio.mimsave(filename, images, duration = .5, loop = 0)
        return filename
    

    def create_gif(self, filenames):
        images = []
        filenames.sort(key=lambda x: int(re.search(r"\d+", x).group()))
        for filename in filenames:
            images.append(imageio.imread(filename))

        imageio.mimsave(filename, images, duration = .5, loop = 0)
        return filename

    def create_single_balloon_map(self, lat, long, elevation, filename, image = None, color = (0,0,0), alpha = 1, radius = 5):
        if image is None:
            image = cv2.imread(self.base_map)
            
        lats        = [lat]
        longs       = [long]
        elevations  = [elevation]
        
        result = image.copy()
        result = self.create_map(image=result, lats=lats, longs=longs, elevations=elevations, filename=filename, save = True, color = color, radius = radius, alpha = alpha)
        return result



    def create_current_map(self, df, hour = 0, filename= None):
        if filename is None:
            filename = f"{self.image_folder}current_positions_{hour}.png"
        lats        = df[df["Hour"] == hour]["Latitude"].to_list()
        longs       = df[df["Hour"] == hour]["Longitude"].to_list()
        elevations  = df[df["Hour"] == hour]["Elevation"].to_list()

            
        image = cv2.imread(self.base_map)
        result = image.copy()
        result = self.create_map(result, lats, longs, elevations, 1, filename, save = True)
                

    def create_map(self, image, lats, longs, elevations, alpha = 1.0, filename = "pinned", save=True, color = (0,0,0), radius = 5):
        # Data must be a list of lists. 
        
        result = image.copy()
        zoom = math.log2(image.shape[1]/256)
        for balloon_number in range(len(lats)):
            location = lats[balloon_number], longs[balloon_number], elevations[balloon_number]
            if np.isnan(location[0]) or np.isnan(location[1]):
                continue
            point = loc2pixels((location[0], location[1]), zoom)
            pixels = point[0], point[1], location[2]

            result = pin(result, pixels, alpha, color = color, radius = radius) 
        if save:
            cv2.imwrite(f"{filename}", result) 
        return result


    
    def get_positions(self, df, hour = 0):  
        image = cv2.imread(self.base_map)
        lats        = df[df["Hour"] == hour]["Latitude"].to_list()
        longs       = df[df["Hour"] == hour]["Longitude"].to_list()
        elevations  = df[df["Hour"] == hour]["Elevation"].to_list()
        speeds  = df[df["Hour"] == hour]["Speed"].to_list()
        bearings  = df[df["Hour"] == hour]["Bearing"].to_list()
        hours  = df[df["Hour"] == hour]["Hour"].to_list()
        zoom = math.log2(image.shape[1]/256)
        pixels = []
        for balloon_number in range(len(lats)):
            location = lats[balloon_number], longs[balloon_number], elevations[balloon_number]
            speed = speeds[balloon_number]
            bearing = bearings[balloon_number]
            hour1 = hours[balloon_number]
            if np.isnan(location[0]) or np.isnan(location[1]):
                continue
            x,y = loc2pixels((location[0], location[1]), zoom)
            if math.isnan(speed):
                speed = -1
            if math.isnan(bearing):
                bearing = -1
            pixels.append({"id": balloon_number, "x" : x, "y": y, "lat" : location[0], "long": location[1], "alt": location[2], "speed":speed, "bearing": bearing, "hour": hour1})
        return pixels
    

        
   


    def get_wind_column(self, df, lat, long, time):
        df = self.winddata
        df = df[df["Latitude"] == lat]
        df = df[df["Longitude"] == long]
        df = self.winddata[self.winddata["Datetime"].astype(str) == str(time)]
        return df     


    def visualize_wind(self, elevations, wind_speeds, wind_directions, filename = "wind_column/foo.png", balloon_elevation = None, balloon_number = -1, hour = 0):
        wind_speeds = (wind_speeds - min(wind_speeds))/ (max(wind_speeds)-min(wind_speeds))
        wind_speeds = wind_speeds * 1
        u = -wind_speeds * np.sin(np.radians(wind_directions))
        v = -wind_speeds * np.cos(np.radians(wind_directions))
        w = np.zeros_like(u)  # No vertical component
        elevations = np.array(elevations)
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        # Starting positions (all arrows originate from x=0, y=0)
        x = np.zeros(len(elevations))
        y = np.zeros(len(elevations))
        z = np.array(elevations)

        fig = plt.figure()

        ax = fig.add_subplot(111, projection='3d')
        for i in range(len(elevations)):
            a = Arrow3D([x[i], u[i]], [y[i], v[i]], 
                [z[i], z[i]], mutation_scale=5, 
                lw=.75, arrowstyle="-|>", color="r")
            ax.add_artist(a)

        # ax.set_xlabel('East → West')
        # ax.set_ylabel('North → South')
        ax.set_zlabel('Altitude (m)')
        ax.set_title(f'3D Wind Profile #{balloon_number} Hour: {hour}')


        max_uv = max(np.max(np.abs(u)), np.max(np.abs(v))) or 1 
        ax.set_xlim(-max_uv, max_uv)
        ax.set_ylim(-max_uv, max_uv)

        
        ax.set_zlim(np.min(z) - 1, np.max(z) + 1)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xticklabels([])
        ax.set_yticklabels([])

        ax.grid(True)

        if balloon_elevation is not None:
            ax.scatter(0, 0, balloon_elevation, color='black', s=50, zorder=10)


        ax.grid(False)
        ax.xaxis.pane.set_edgecolor('none')
        ax.yaxis.pane.set_edgecolor('none')
        ax.zaxis.pane.set_edgecolor('none')
        ax.set_axis_off()
        ax.set_zticks([])
        ax.set_zticklabels([])
        ax.set_zlabel('')

        # Z axis
        ax.add_line(Line3D(
            [1, 1], [1, 1], [0, max(elevations)-1], 
            color='black', lw=1, 
        ))


        # Side 1
        ax.add_line(Line3D(
            [1, 1], [1, -1], [0, 0],  # x, y, z coordinates
            color='black', lw=1,  # Style as needed
        ))

        ax.add_line(Line3D(
            [1, -1], [1, 1], [0, 0],  # x, y, z coordinates
            color='black', lw=1,  # Style as needed
        ))

       
        label_params = {
        "North": (0, 1.1, 0),  # Midpoint of the North edge
        "South": (0, -1.1, 0), # Midpoint of the South edge
        "East": (1.1, 0, 0),   # Midpoint of the East edge
        "West": (-1.1, 0, 0),  # Midpoint of the West edge
        }
        for label, (x, y, z) in label_params.items():
            ax.text(x, y, z, label, color='blue', fontsize=10, ha='center', va='center')

        ax.text(1, 1, max(elevations),  "Altitude (km)", color='black', fontsize=10, ha='center', va='center')
        for elevation in elevations:
            ax.text(1, 1, elevation,  f"-", color='grey', fontsize=20, ha='center', va='center')
            ax.text(1.1, 1.1, elevation,  f"{elevation} ", color='grey', fontsize=5, ha='center', va='center')

        def animate(frame):
            ax.view_init(elev=30, azim=frame)  # Rotate horizontally
            return fig,

        # Create animation
        ani = FuncAnimation(fig, animate, frames=np.arange(0, 360, 2), interval=50)
        ani.save(filename, writer='pillow')
        matplotlib.pyplot.close()

class Arrow3D(FancyArrowPatch):
    def __init__(self, xs, ys, zs, *args, **kwargs):
        FancyArrowPatch.__init__(self, (0,0), (0,0), *args, **kwargs)
        self._verts3d = xs, ys, zs

    def do_3d_projection(self, renderer=None):
        xs3d, ys3d, zs3d = self._verts3d
        xs, ys, zs = proj3d.proj_transform(xs3d, ys3d, zs3d, self.axes.M)
        self.set_positions((xs[0],ys[0]),(xs[1],ys[1]))

        return np.min(zs)


        
        



