from tools import pin, loc2pixels
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.patches import FancyArrowPatch
from mpl_toolkits.mplot3d import proj3d
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d.art3d import Line3D


class Visualizer:
    def __init__(self):
        self.balloon_data = pd.read_csv("./data/Windborne.csv")
        self.winddata     = pd.read_csv("./data/data.csv")


        
    def get_wind_column(self, df, lat, long, time):
        df = self.winddata
        df = df[df["Latitude"] == lat]
        df = df[df["Longitude"] == long]
        df = self.winddata[self.winddata["Datetime"].astype(str) == str(time)]
        return df
    
   
    def visualize_wind(self, elevations, wind_speeds, wind_directions, filename = "wind_column/foo.png", balloon_elevation = None):
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
        ax.set_title('3D Wind Profile')


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


        plt.savefig(filename)
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
        ani.save('rotation.gif', writer='pillow')

class Arrow3D(FancyArrowPatch):
    def __init__(self, xs, ys, zs, *args, **kwargs):
        FancyArrowPatch.__init__(self, (0,0), (0,0), *args, **kwargs)
        self._verts3d = xs, ys, zs

    def do_3d_projection(self, renderer=None):
        xs3d, ys3d, zs3d = self._verts3d
        xs, ys, zs = proj3d.proj_transform(xs3d, ys3d, zs3d, self.axes.M)
        self.set_positions((xs[0],ys[0]),(xs[1],ys[1]))

        return np.min(zs)


        
        



