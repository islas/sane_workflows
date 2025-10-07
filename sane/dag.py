import queue
import copy


class DAG:
  def __init__( self ):
    self._nodes  = {}
    self._rnodes = {}

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

  def traversal_to( self, nodes ):
    traversal  = []
    current    = []
    next_nodes = nodes.copy()

    while len( next_nodes ) > 0:
      current = next_nodes.copy()
      next_nodes.clear()
      visited = []

      while len( current ) > 0:
        key = current.pop()
        next_nodes.extend( self._rnodes[key] )

        visited.append( key )

      traversal.append( list( set( visited ) ) )

    # Clean it up
    for i in reversed( range( 0, len( traversal ) ) ):
      # For all previous appearing keys
      for key in traversal[i]:
        # Check prior listings and remove them since they are already listed
        for j in range( 0, i ):
          if key in traversal[j]:
            traversal[j].remove( key )

    return list( reversed( traversal ) )

  def traversal_list( self, nodes ):
    traversal_directed = self.traversal_to( nodes )
    traversal = { key : len( self._rnodes[key] ) for node_set in traversal_directed for key in node_set }
    return traversal

  # This could be a static method but as traversal_list and node_complete are not
  # to give a similar interfacing I am keeping this as an instance method
  def get_next_nodes( self, traversal_list ):
    nodes = [ key for key, count in traversal_list.items() if count == 0]
    for n in nodes:
      del traversal_list[n]
    return nodes

  def node_complete( self, node, traversal_list ):
    for child in self._nodes[node]:
      if child in traversal_list:
        traversal_list[child] -= 1
