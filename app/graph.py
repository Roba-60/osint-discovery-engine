import networkx as nx
from typing import List, Dict, Any

class IdentityGraphBuilder:
    def __init__(self):
        self.graph = nx.DiGraph()

    def build_identity_network(self, seed_type: str, seed_value: str, discoveries: List[Dict[str, Any]]) -> Dict[str, Any]:
        seed_id = f"seed:{seed_type}:{seed_value}"
        self.graph.add_node(seed_id, label=seed_value, node_type="seed", category=seed_type)

        for item in discoveries:
            platform = item.get("platform", "Unknown")
            url = item.get("profile_url", "")
            target_id = f"entity:{platform}:{url}"

            self.graph.add_node(
                target_id,
                label=platform,
                profile_url=url,
                node_type="discovered_profile"
            )

            # Add directed edge with confidence score
            self.graph.add_edge(seed_id, target_id, weight=0.85, relation="POSSIBLE_ACCOUNT")

        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "graph_data": nx.node_link_data(self.graph)
        }
