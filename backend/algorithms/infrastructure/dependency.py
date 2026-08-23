class DependencyBuilder:
    def __init__(self, raw_infrastructure_data):
        """
        Ingests the raw infrastructure nodes and builds the directional edges.
        """
        self.nodes = raw_infrastructure_data['infrastructure']
        self.graph = {node['id']: [] for node in self.nodes}
        
        # Populate the adjacency list for dependencies
        for node in self.nodes:
            if 'depends_on' in node:
                for dep in node['depends_on']:
                    # The parent points to the child (Direction of flow/support)
                    self.graph[dep['parent_id']].append(node['id'])

    def validate_architecture(self):
        """
        Runs cycle detection to ensure the dependency graph is a valid DAG.
        Returns True if safe, raises an error if a logical loop is found.
        """
        visited = set()
        recursion_stack = set()
        
        def dfs(node_id):
            visited.add(node_id)
            recursion_stack.add(node_id)
            
            for child_id in self.graph.get(node_id, []):
                if child_id not in visited:
                    if dfs(child_id):
                        return True
                elif child_id in recursion_stack:
                    # A cycle is detected! 
                    raise ValueError(f"Circular dependency detected involving node: {child_id}")
                    
            recursion_stack.remove(node_id)
            return False
            
        for node in self.graph.keys():
            if node not in visited:
                dfs(node)
                
        return True

    def get_critical_paths(self):
        """
        Identifies 'root' nodes (those with no dependencies) 
        which represent single points of failure for the broader network.
        """
        roots = []
        for node in self.nodes:
            if not node.get('depends_on'):
                roots.append(node['id'])
        return roots