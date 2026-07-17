import json
import math
import heapq
import os
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

class RouteGraph:
    def __init__(self):
        # We will map each unique (x, y) node to an integer ID
        self.nodes: Dict[int, Tuple[float, float]] = {}
        self.node_hexes: Dict[int, str] = {}
        self.edges: Dict[int, List[Tuple[int, float]]] = defaultdict(list)
        self._next_node_id = 0
        
        # Spatial hash grid for fast node merging
        self._grid: Dict[Tuple[int, int], List[int]] = defaultdict(list)
        self.grid_size = 80.0 # Tolerance for node merging in pixels

    def _get_or_create_node(self, x: float, y: float, hex_name: str = "", tolerance: float = 80.0) -> int:
        grid_x = int(x // self.grid_size)
        grid_y = int(y // self.grid_size)
        
        # Search neighboring cells for a node within tolerance
        best_id = -1
        best_dist = tolerance * tolerance
        
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                cell = (grid_x + dx, grid_y + dy)
                if cell in self._grid:
                    for node_id in self._grid[cell]:
                        nx, ny = self.nodes[node_id]
                        dist_sq = (nx - x)**2 + (ny - y)**2
                        if dist_sq < best_dist:
                            best_dist = dist_sq
                            best_id = node_id
                            
        if best_id != -1:
            return best_id
            
        # Create new node
        new_id = self._next_node_id
        self._next_node_id += 1
        self.nodes[new_id] = (x, y)
        self.node_hexes[new_id] = hex_name
        self._grid[(grid_x, grid_y)].append(new_id)
        return new_id

    def load_from_json(self, filepath: str) -> None:
        if not os.path.exists(filepath):
            print(f"[Routing] Error: {filepath} not found.")
            return

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        weights = {
            "estrada_nivel_1": 1.0,
            "estrada_nivel_2": 1.5,
            "estrada_nivel_3": 2.5
        }

        for hex_name, hex_data in data.items():
            for level, segments in hex_data.items():
                cost_multiplier = weights.get(level, 3.0)
                
                for segment in segments:
                    if len(segment) < 2:
                        continue
                        
                    # Process pairs of points in the polyline
                    # We removed interpolation and rely on 80.0 tolerance to merge left/right perimeters
                    # into a smooth centerline graph natively.
                    prev_id = self._get_or_create_node(segment[0][0], segment[0][1], hex_name)
                    for i in range(1, len(segment)):
                        curr_id = self._get_or_create_node(segment[i][0], segment[i][1], hex_name)
                        
                        if prev_id != curr_id:
                            x1, y1 = self.nodes[prev_id]
                            x2, y2 = self.nodes[curr_id]
                            distance = math.hypot(x2 - x1, y2 - y1)
                            cost = distance * cost_multiplier
                            
                            # Add undirected edge
                            self.edges[prev_id].append((curr_id, cost))
                            self.edges[curr_id].append((prev_id, cost))
                            
                        prev_id = curr_id
                        
        print(f"[Routing] Graph loaded: {len(self.nodes)} nodes, {sum(len(e) for e in self.edges.values())} edges.")
        self._post_process_graph()
        
    def _post_process_graph(self, connect_dist: float = 120.0) -> None:
        # Find all connected components
        visited = set()
        comps = []
        for n in self.nodes:
            if n not in visited:
                comp = set()
                q = [n]
                visited.add(n)
                while q:
                    curr = q.pop()
                    comp.add(curr)
                    for nxt, _ in self.edges[curr]:
                        if nxt not in visited:
                            visited.add(nxt)
                            q.append(nxt)
                comps.append(comp)
        
        # Precompute bounding boxes and node coordinates for fast check
        comp_data = []
        for c in comps:
            xs = [self.nodes[n][0] for n in c]
            ys = [self.nodes[n][1] for n in c]
            comp_data.append({
                'nodes': c,
                'min_x': min(xs), 'max_x': max(xs),
                'min_y': min(ys), 'max_y': max(ys)
            })
            
        # Connect nearby components
        edges_added = 0
        for i in range(len(comp_data)):
            c1 = comp_data[i]
            for j in range(i+1, len(comp_data)):
                c2 = comp_data[j]
                if c1['min_x'] > c2['max_x'] + connect_dist or c1['max_x'] < c2['min_x'] - connect_dist:
                    continue
                if c1['min_y'] > c2['max_y'] + connect_dist or c1['max_y'] < c2['min_y'] - connect_dist:
                    continue
                    
                # Find closest pair
                min_d = float('inf')
                best_pair = None
                for n1 in c1['nodes']:
                    x1, y1 = self.nodes[n1]
                    for n2 in c2['nodes']:
                        x2, y2 = self.nodes[n2]
                        if abs(x1-x2) < connect_dist and abs(y1-y2) < connect_dist:
                            d = math.hypot(x1-x2, y1-y2)
                            if d < min_d:
                                min_d = d
                                best_pair = (n1, n2)
                
                if min_d <= connect_dist and best_pair:
                    n1, n2 = best_pair
                    # Heavy penalty for off-road/bridge jumps so A* only uses them as a last resort
                    # rather than as shortcuts across rivers.
                    cost = min_d * 50.0 
                    self.edges[n1].append((n2, cost))
                    self.edges[n2].append((n1, cost))
                    edges_added += 1
                    
        print(f"[Routing] Post-processing finished. {edges_added} bridge edges added to connect components.")

    def _find_closest_node(self, x: float, y: float) -> Optional[int]:
        if not self.nodes:
            return None
            
        # First try to find in grid
        grid_x = int(x // self.grid_size)
        grid_y = int(y // self.grid_size)
        
        search_radius = 1
        best_id = None
        best_dist = float('inf')
        
        # Increase search radius until we find a node, max radius to avoid full scan if possible
        while search_radius < 50 and best_id is None:
            for dx in range(-search_radius, search_radius + 1):
                for dy in range(-search_radius, search_radius + 1):
                    cell = (grid_x + dx, grid_y + dy)
                    if cell in self._grid:
                        for node_id in self._grid[cell]:
                            nx, ny = self.nodes[node_id]
                            dist = (nx - x)**2 + (ny - y)**2
                            if dist < best_dist:
                                best_dist = dist
                                best_id = node_id
            search_radius += 2
            
        # Fallback to full scan if nothing found in local grid
        if best_id is None:
            for node_id, (nx, ny) in self.nodes.items():
                dist = (nx - x)**2 + (ny - y)**2
                if dist < best_dist:
                    best_dist = dist
                    best_id = node_id
                    
        return best_id

    def calculate_route(self, start_x: float, start_y: float, end_x: float, end_y: float) -> Tuple[List[Tuple[float, float]], float, float]:
        """
        Calculates the fastest route between two points using A*.
        Returns a tuple of (path_coordinates, total_distance, estimated_time).
        """
        start_node = self._find_closest_node(start_x, start_y)
        end_node = self._find_closest_node(end_x, end_y)
        
        if start_node is None or end_node is None:
            return [], 0.0, 0.0

        # A* algorithm
        def heuristic(n1: int, n2: int) -> float:
            x1, y1 = self.nodes[n1]
            x2, y2 = self.nodes[n2]
            return math.hypot(x2 - x1, y2 - y1)

        open_set = []
        heapq.heappush(open_set, (0.0, start_node))
        
        came_from = {}
        g_score = {start_node: 0.0}
        f_score = {start_node: heuristic(start_node, end_node)}
        
        while open_set:
            current_f, current = heapq.heappop(open_set)
            
            if current == end_node:
                # Reconstruct path
                path = []
                curr = current
                while curr in came_from:
                    path.append(self.nodes[curr])
                    curr = came_from[curr]
                path.append(self.nodes[start_node])
                path.reverse()
                
                # Ensure the actual requested start and end points are included without duplication
                if not path or path[0] != (start_x, start_y):
                    path.insert(0, (start_x, start_y))
                if path[-1] != (end_x, end_y):
                    path.append((end_x, end_y))
                
                # Estimate distance and time
                total_cost = g_score[end_node]
                base_speed = 1000.0 
                estimated_time_mins = total_cost / base_speed
                
                # Write to debug log
                try:
                    with open("route_debug.log", "w") as f:
                        f.write(f"Route Calculated Successfully!\n")
                        f.write(f"Start: ({start_x:.1f}, {start_y:.1f}) -> End: ({end_x:.1f}, {end_y:.1f})\n")
                        f.write(f"Total Nodes traversed: {len(path)}\n")
                        f.write(f"Estimated Cost: {total_cost:.1f}\n")
                        for i, p in enumerate(path):
                            f.write(f"Node {i}: {p[0]:.1f}, {p[1]:.1f}\n")
                except:
                    pass
                
                return path, total_cost, estimated_time_mins
                
            for neighbor, cost in self.edges[current]:
                tentative_g_score = g_score[current] + cost
                
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + heuristic(neighbor, end_node)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
                    
        # Write to debug log if failed
        try:
            with open("route_debug.log", "w") as f:
                f.write(f"Route Failed!\n")
                f.write(f"Start: ({start_x:.1f}, {start_y:.1f}) -> End: ({end_x:.1f}, {end_y:.1f})\n")
                f.write(f"Open set exhausted. No path found.\n")
        except:
            pass
            
        return [], 0.0, 0.0

# Singleton instance to be used by the controller
_graph = None

def get_routing_graph() -> RouteGraph:
    global _graph
    if _graph is None:
        _graph = RouteGraph()
    return _graph
