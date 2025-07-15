#!/usr/bin/env python3


import dag
from Action import Action

graph = dag.DAG()

a = Action( "a" )
b = Action( "b" )
c = Action( "c" )
d = Action( "d" )


e = Action( "e" )
f = Action( "f" )
g = Action( "g" )
h = Action( "h" )
i = Action( "i" )
j = Action( "j" )
k = Action( "k" )
l = Action( "l" )
actions = [ a, b, c, d, e, f, g, h, h, i, j, k, l ]
for act in actions:
  act.verbose_ = True
  act.set_config(
    {
      "command"   : "echo",
      "arguments" : act.id_
    }
  )


graph.add_edge( a, b )
graph.add_edge( a, c )
graph.add_edge( c, d )
graph.add_edge( b, d )
graph.add_edge( a, d )

graph.add_edge( e, f )
graph.add_edge( e, g )
graph.add_edge( e, h )
graph.add_edge( h, i )
graph.add_edge( h, j )
graph.add_edge( g, j )
graph.add_edge( f, i )
graph.add_edge( j, k )
graph.add_edge( k, l )

print( graph.topological_sort() )

print( graph.traversal_to( [ d, l ] ) )
traversal_list = graph.traversal_list( [d, l] )
print( "traversal_list" )
print( traversal_list )

while len( traversal_list ) > 0:
  next_nodes = graph.get_next_nodes( traversal_list )
  print( f"Doing nodes : {next_nodes}")
  for node in next_nodes:
    node.launch()
    graph.node_complete( node, traversal_list )

print( "Finished" )
