from src.data_collector import DataCollector
from src.tools import earth_distance, move_distance_to_lat_long
import numpy as np # idk i have done this for too long
class Node:
    def __init__(self, lat, long, alt, hour, parent, children = [], id = -1, distance = float("inf")):
        self.location = lat, long
        self.lat      = lat
        self.long     = long
        self.hour     = hour
        self.alt      = alt
        self.id       = id
        self.children = children
        self.parent   = parent
        self.distance = distance
        self.signature = f"{lat},{long},{hour}"


    def add_child(self, child):
        self.children.append(child)
        return child
    def get_child(self, index):
        return self.children[index]
    def length(self):
        return len(self.children) 
    def __str__(self):
        stringer = f"{self.id}"
        stringer = f"{self.id} | {self.lat:.4f} | {self.long:.4f} | Distance {self.distance} |"
        if not self.parent is None:
            stringer += f" Parent: {self.parent.id}"
        return stringer

class Navigator:
    # This is a fake init which only runs because of the web app thing
    def __init__(self):
        self.dc               = DataCollector()

    def set_values(self, starting_location, target_location, tolerance = 10, beam_width = 5):
        self.current_id       = 0
        self.hour             = 0
        self.current_node     = self.add_node(lat = starting_location[0], long = starting_location[1], alt = -1, hour = self.hour, parent=None, distance = earth_distance(starting_location, target_location)[0])
        self.target_location  = target_location
        self.locations        = [starting_location]
        self.current_list     = [self.current_node]
        self.tolerance        = tolerance
        self.beam_width       = beam_width


    def add_node(self, lat, long, alt, hour, parent, children = [], distance = float("inf")):
        self.current_id = self.current_id + 1 
        return Node(
            lat, long, alt, hour, 
            parent, children, 
            self.current_id,
            distance)


    def beam_search(self, max_iters = 20):
        node = self.current_node
        for index in range(max_iters):
            new_list = []
            
            closest_node = self.get_closest_node(self.current_list)
            print(f"{index/max_iters:.2f} {closest_node} | Calls {self.dc.num_api_calls}")
            
            children = self.explore_nodes(self.current_list)
            signatures = set()
            for child in children:
                if child.signature in signatures:
                    continue
                signatures.add(child.signature)
                if child.distance < self.tolerance:
                    return child
                if len(new_list) < self.beam_width:
                    new_list.append(child)
                    continue
                max_node = self.get_furthest_node(new_list)
                if child.distance < max_node.distance:
                    new_list.remove(max_node)
                    new_list.append(child)
            
            if len(new_list) == 0:
                print("Warning: No valid nodes to explore.")
                return closest_node
            self.current_list = new_list

        closest_node = self.get_closest_node(self.current_list)
        print("Failed to find a path close")
        return closest_node

    def get_path_json(self, node):
        nodes = []
        while node.id != 1:
            if node.parent is None:
                return nodes
            speed, bearing = earth_distance((node.lat, node.long), (node.parent.lat, node.parent.long))
            bearing = np.float64(bearing)
            nodes.append({
                "time"       : self.dc.hour2time(node.hour).strftime("%m-%d %H:%M"),
                "lat"        : node.lat,
                "long"       : node.long,
                "alt"        : node.alt,
                "speed"      : speed,
                "bearing"    : bearing,
                "distance"   : node.distance,

            })
            node = node.parent
        nodes.reverse()
        return nodes
    
    def get_path_lat_long(self, node):
        nodes = []
        while node.id != 1:
            nodes.append([node.lat,node.long,node.alt])
            node = node.parent
        nodes.reverse()
        return nodes

    def explore_nodes(self, nodes):
        print(f"Node Length: {len(nodes)}")
        if len(nodes) == 1:
            return self.explore_node(nodes[0])
        results = self.get_wind_state_multi_loc(nodes)
        for node in nodes:
            speeds, bearings, alts = results[node.id]
            if speeds is None:
                return []
            length = len(speeds)
            children = []
            for i in range(length):
                location = move_distance_to_lat_long(node.lat, node.long, speeds[i], bearings[i])
                distance = earth_distance(location, self.target_location)[0]
                lat, long = location[0], location[1]
                child = self.add_node(lat, long, alts[i], hour = node.hour+1, parent = node, distance = distance)
                node.add_child(child)
                children.append(child)
            return children
    

    def get_wind_state_multi_loc(self, nodes):
        locations = []
        for node in nodes:
            locations.append((node.lat, node.long))
            
        query_time = self.dc.hour2time(nodes[0].hour)
        df = self.dc.get_and_save_wind_multi_loc(locations=locations, query_time=query_time)
        if len(df) == 0:
            return None, None, None
        results = {}
        for node in nodes:
            speeds = df["Speed"].tolist()
            bearings = df["Bearing"].tolist()
            alts = df["Elevation"].tolist()
            results[node.id] = (speeds, bearings, alts)
        return results
    
    def get_wind_state(self, node):
        time = self.dc.hour2time(node.hour)
        df = self.dc.get_and_save_wind(lat = node.lat, long = node.long, time = time)
        if len(df) == 0:
            return None, None, None
        speeds = df["Speed"].tolist()
        bearings = df["Bearing"].tolist()
        alts = df["Elevation"].tolist()
        return speeds, bearings, alts
        
    def explore_node(self, node):
        speeds, bearings, alts = self.get_wind_state(node)
        if speeds is None:
            return []
        length = len(speeds)
        children = []
        for i in range(length):
            location = move_distance_to_lat_long(node.lat, node.long, speeds[i], bearings[i])
            distance = earth_distance(location, self.target_location)[0]
            lat, long = location[0], location[1]
            child = self.add_node(lat, long, alts[i], hour = node.hour+1, parent = node, distance = distance)
            node.add_child(child)
            children.append(child)
        return children

    def get_closest_node(self, nodes):
        distance = float("inf")
        best_node = None
        for node in nodes:
            if node.distance < distance:
                best_node = node
                distance = node.distance
        return best_node
    

    def get_furthest_node(self, nodes):
        distance = 0
        best_node = None
        for node in nodes:
            if node.distance > distance:
                best_node = node
                distance = node.distance
        return best_node
    



"""
            return

            for j in range(len(self.current_list)):
                node = self.current_list[j]
                children = self.explore_node(node)
"""



    