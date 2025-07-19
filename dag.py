import queue
import copy

class DAG:
  def __init__( self ):
    self.nodes_  = {}
    self.rnodes_ = {}

  def add_node( self, node ):
    if node not in self.nodes_:
      self.nodes_[node] = []
    if node not in self.rnodes_:
      self.rnodes_[node] = []

  def add_edge( self, parent, child ):
    self.add_node( parent )
    self.add_node( child  )

    self.nodes_[parent].append( child )
    self.rnodes_[child].append( parent )
  

  def topological_sort( self ):
    in_degree = { key : len(self.rnodes_[key]) for key in self.nodes_.keys() }

    need_to_visit = queue.Queue()

    for key, degrees in in_degree.items():
      if degrees == 0:
        need_to_visit.put( key )
    
    sort_order = []
    while not need_to_visit.empty():
      key = need_to_visit.get()
      
      if in_degree[key] == 0:
        sort_order.append( key )
      
      for neighbor in self.nodes_[key]:
        in_degree[neighbor] -= 1
        if in_degree[neighbor] == 0:
          need_to_visit.put( neighbor )

    if len( sort_order ) == len( self.nodes_.keys() ):
      print( "Sorted correctly" )
      return sort_order, True
    else:
      print( "Error: Contains a cycle!" )
      print( "  See the following nodes: " )
      not_visited = [ key for key in self.nodes_.keys() if in_degree[key] >= 1 ]
      print( not_visited )
      return not_visited, False
  

  def traversal_to( self, nodes ):
    traversal  = []
    current    = []
    next_nodes = nodes

    while len( next_nodes ) > 0:
      current = next_nodes.copy()
      next_nodes.clear()
      visited = []

      while len( current ) > 0:
        key = current.pop()
        next_nodes.extend( self.rnodes_[key] )

        visited.append( key )

      traversal.append( list( set( visited ) ) )

    # Clean it up
    for i in reversed( range( 0, len( traversal ) ) ) :
      # For all previous appearing keys
      for key in traversal[i]: 
        # Check prior listings and remove them since they are already listed
        for j in range( 0, i ) :
          if key in traversal[j]:
            traversal[j].remove( key )

    return list( reversed( traversal ) )

  def traversal_list( self, nodes ):
    traversal_directed = self.traversal_to( nodes )
    traversal = { key : len( self.rnodes_[key] ) for l in traversal_directed for key in l }
    return traversal
  
  # This could be a static method but as traversal_list and node_complete are not
  # to give a similar interfacing I am keeping this as an instance method
  def get_next_nodes( self, traversal_list ):
    nodes = [ key for key, count in traversal_list.items() if count == 0]
    for n in nodes:
      del traversal_list[n]
    return nodes

  def node_complete( self, node, traversal_list ):
    for child in self.nodes_[node]:
      if child in traversal_list:
        traversal_list[child] -= 1

