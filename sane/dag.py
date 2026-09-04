import queue
import collections


class DAG:
  def __init__( self ):
    self._nodes  = collections.OrderedDict()
    self._rnodes = collections.OrderedDict()

  def clear( self ):
    self._nodes.clear()
    self._rnodes.clear()

  def add_node( self, node ):
    if node not in self._nodes:
      self._nodes[node] = []
    if node not in self._rnodes:
      self._rnodes[node] = []

  def add_edge( self, parent, child ):
    self.add_node( parent )
    self.add_node( child  )

    self._nodes[parent].append( child )
    self._rnodes[child].append( parent )

  def topological_sort( self ):
    in_degree = { key : len(self._rnodes[key]) for key in self._nodes.keys() }

    need_to_visit = queue.Queue()

    for key, degrees in in_degree.items():
      if degrees == 0:
        need_to_visit.put( key )

    sort_order = []
    while not need_to_visit.empty():
      key = need_to_visit.get()

      if in_degree[key] == 0:
        sort_order.append( key )

      for neighbor in self._nodes[key]:
        in_degree[neighbor] -= 1
        if in_degree[neighbor] == 0:
          need_to_visit.put( neighbor )

    if len( sort_order ) == len( self._nodes.keys() ):
      return sort_order, True
    else:
      print( "Error: Contains a cycle!" )
      print( "  See the following nodes: " )
      not_visited = [ key for key in self._nodes.keys() if in_degree[key] >= 1 ]
      print( not_visited )
      return not_visited, False

  def traversal_to( self, end_nodes, start_nodes=None ):
    """Find traversal path from start nodes to end nodes in the DAG.

    If start_nodes is None, finds all ancestors of end_nodes (backward traversal).

    If start_nodes is specified, finds the subgraph containing all nodes on paths
    from start_nodes to end_nodes. If a node in end_nodes is not reachable it is not
    listed in the traversal

    :return: List of lists representing layers from start to end nodes
    """
    # Backward traversal: find all ancestors of end_nodes
    traversal_backward = []
    current = []
    next_nodes = end_nodes.copy()

    while len( next_nodes ) > 0:
      current = next_nodes.copy()
      next_nodes.clear()
      visited = []

      while len( current ) > 0:
        key = current.pop()
        next_nodes.extend( self._rnodes[key] )

        visited.append( key )

      traversal_backward.append( list( set( visited ) ) )

    # Clean up duplicates
    for i in reversed( range( 0, len( traversal_backward ) ) ):
      for key in traversal_backward[i]:
        for j in range( 0, i ):
          if key in traversal_backward[j]:
            traversal_backward[j].remove( key )

    if start_nodes is None:
      # Original behavior: return full ancestry
      return list( reversed( traversal_backward ) )

    # Filter to subgraph: intersection of ancestors and descendants
    ancestors_set = set( node for level in traversal_backward for node in level )

    # Forward traversal: find all descendants of start_nodes
    descendants_set = set( start_nodes )
    to_visit = list( start_nodes )
    while len( to_visit ) > 0:
      node = to_visit.pop( 0 )
      for child in self._nodes[node]:
        if child not in descendants_set:
          descendants_set.add( child )
          to_visit.append( child )

    # Valid nodes: both ancestors of end AND descendants of start
    valid_nodes = ancestors_set & descendants_set

    # Rebuild traversal with only valid nodes
    result = []
    for level in traversal_backward:
      valid_in_level = [ n for n in level if n in valid_nodes ]
      if valid_in_level:
        result.append( valid_in_level )

    return list( reversed( result ) )

  def traversal_list( self, nodes ):
    traversal_directed = self.traversal_to( nodes )
    traversal = { key : len( self._rnodes[key] ) for node_set in traversal_directed for key in node_set }
    return traversal

  # This could be a static method but as traversal_list and node_complete are not
  # to give a similar interfacing I am keeping this as an instance method
  def get_next_nodes( self, traversal_list ):
    # Make the intra-level traversal deterministic based on order of node insertion
    nodes = sorted( [ key for key, count in traversal_list.items() if count == 0], key=list(self._nodes.keys()).index )
    for n in nodes:
      del traversal_list[n]
    return nodes

  def node_complete( self, node, traversal_list ):
    for child in self._nodes[node]:
      if child in traversal_list:
        traversal_list[child] -= 1
