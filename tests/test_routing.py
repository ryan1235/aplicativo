import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from foxmap.geo.routing import get_routing_graph
import json

def test_routing():
    # Create a small mock roads.json
    mock_data = {
        "TestHex": {
            "estrada_nivel_1": [
                [[0, 0], [100, 0], [100, 100]],
                [[105, 100], [200, 100]] # Small gap of 5 pixels, should merge
            ]
        }
    }
    
    with open("mock_roads.json", "w") as f:
        json.dump(mock_data, f)
        
    graph = get_routing_graph()
    graph.load_from_json("mock_roads.json")
    
    # Check if nodes merged
    # There should be:
    # 0,0 -> Node 0
    # 100,0 -> Node 1
    # 100,100 -> Node 2
    # 105,100 -> Node 2 (merged since dist < 20)
    # 200,100 -> Node 3
    
    assert len(graph.nodes) == 4, f"Expected 4 nodes, got {len(graph.nodes)}"
    
    # Calculate route from (0,0) to (200,100)
    path, cost, time = graph.calculate_route(0, 0, 200, 100)
    
    print(f"Path: {path}")
    print(f"Cost: {cost}")
    print(f"Time: {time}")
    
    assert len(path) == 4, f"Expected 4 points in path (start + 2 nodes + end), got {len(path)}"
    
    print("Routing logic works!")

if __name__ == "__main__":
    test_routing()
