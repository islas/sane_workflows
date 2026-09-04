import unittest

from sane.dag import DAG
from sane.dagvis import visualize as dagvis


class DagTests( unittest.TestCase ):

  def setUp( self ):
    self.dag = DAG()

  def dag_valid( self, nodes, valid ):
    self.assertTrue( valid )
    for node in nodes:
      self.assertIn( node, self.dag._nodes )
    self.assertEqual( len( nodes ), len( self.dag._nodes ) )

  def dag_invalid( self, nodes, valid ):
    self.assertFalse( valid )
    # This cannot be tested like so since all nodes may be problematic
    # self.assertNotEqual( len( nodes ), len( self.dag._nodes ) )

  def validate_traversal( self, traversal_list, expected ):
    step     = 0
    while len( traversal_list ) > 0:
      nodes = self.dag.get_next_nodes( traversal_list )
      for node in nodes:
        self.assertIn( node, expected[step] )
        expected[step].remove( node )

        self.assertNotIn( node, traversal_list )
        self.dag.node_complete( node, traversal_list )
      step += 1

    # All expected should have been visited in this walk
    self.assertEqual( traversal_list, {} )
    for node_list in expected:
      self.assertEqual( node_list, [] )

  def test_dag_no_nodes( self ):
    """A valid DAG consisting of no nodes"""
    nodes, valid = self.dag.topological_sort()
    self.dag_valid( nodes, valid )
    self.assertEqual( nodes, [] )

  def test_dag_single_node( self ):
    """A valid DAG consisting of a single node"""
    self.dag.add_node( "a" )

    nodes, valid = self.dag.topological_sort()
    self.dag_valid( nodes, valid )
    self.assertEqual( nodes, [ "a" ] )

  def test_dag_isolated_nodes( self ):
    """A valid DAG consisting of multiple isolated nodes"""
    self.dag.add_node( "a" )
    self.dag.add_node( "b" )
    self.dag.add_node( "c" )
    self.dag.add_node( "d" )

    nodes, valid = self.dag.topological_sort()
    self.dag_valid( nodes, valid )
    self.assertEqual( nodes, [ "a", "b", "c", "d" ] )

  def test_dag_2node_acyclic( self ):
    """A valid DAG consisting of 2 nodes, one pointing to the other"""
    self.dag.add_node( "a" )
    self.dag.add_node( "b" )
    # this sets up a -> b where b is dependent (child) on a (parent)
    self.dag.add_edge( "a", "b" )

    nodes, valid = self.dag.topological_sort()
    self.dag_valid( nodes, valid )
    self.assertEqual( nodes, [ "a", "b" ] )

  def test_dag_2node_acyclic_via_edge( self ):
    """A valid DAG consisting of 2 nodes, one pointing to the other

    This does not individually create the nodes and then connect them,
    instead creating the nodes via the add_edge() command directly.

    The result should be something identical to the create-then-link DAG
    """
    # this sets up a -> b where b is dependent (child) on a (parent)
    self.dag.add_edge( "a", "b" )

    nodes, valid = self.dag.topological_sort()
    self.dag_valid( nodes, valid )
    self.assertEqual( nodes, [ "a", "b" ] )

  def test_dag_2node_cyclic( self ):
    """An invalid DAG consisting of 2 nodes pointing to each other creating a cycle"""
    self.dag.add_node( "a" )
    self.dag.add_node( "b" )
    # this sets up a -> b where b is dependent (child) on a (parent)
    self.dag.add_edge( "a", "b" )
    # this creates the simplest cycle
    self.dag.add_edge( "b", "a" )

    nodes, valid = self.dag.topological_sort()
    self.dag_invalid( nodes, valid )
    # nodes should now be equal to the potentially bad nodes
    self.assertEqual( nodes, [ "a", "b" ] )

  def test_dag_5node_acyclic_single_entry_single_end( self ):
    """A valid DAG consisting of 5 nodes with one start node and one end node

    The single start node has an in-degree of zero and the path to the final
    node is fully reduced and requires traversal to all other nodes:
          a
          v
          b
        __|__
      v      v
      c      d
      |______|
          |
          v
          e
    """
    # This also tests creation via edge addition
    self.dag.add_edge( "a", "b" )
    self.dag.add_edge( "b", "c" )
    self.dag.add_edge( "b", "d" )
    self.dag.add_edge( "c", "e" )
    self.dag.add_edge( "d", "e" )

    nodes, valid = self.dag.topological_sort()
    self.dag_valid( nodes, valid )
    self.assertEqual( nodes, [ "a", "b", "c", "d", "e" ] )

  def test_dag_5node_acyclic_traversal_to_end( self ):
    """A valid DAG consisting of 5 nodes and testing traversal to the end

    The single start node has an in-degree of zero and the path to the final
    node is fully reduced and requires traversal to all other nodes:
          a
          v
          b
        __|__
      v      v
      c      d
      |______|
          |
          v
          e

    From here, the traversal to "e" should consist of a -> b -> [c, d] -> e
    """
    # Start from this test
    self.test_dag_5node_acyclic_single_entry_single_end()

    traversal_list = self.dag.traversal_to( [ "e" ] )
    # The traversal list is a record of all levels that must be traversed and
    # which nodes in that level to visited. The flattened version should have
    # the total nodes
    print( traversal_list )
    self.assertEqual( len( traversal_list ), 4 )
    self.assertEqual( len( [ node for node_list in traversal_list for node in node_list ] ), len( self.dag._nodes ) )

  def test_dag_5node_acyclic_traversal_list( self ):
    """A valid DAG consisting of 5 nodes and walking the traversal one node at a time

    The single start node has an in-degree of zero and the path to the final
    node is fully reduced and requires traversal to all other nodes:
          a
          v
          b
        __|__
      v      v
      c      d
      |______|
          |
          v
          e

    From here, the traversal to "e" should consist of a -> b -> [c, d] -> e
    Thus, a walk of the traversal using traversal_list() should yield:
    a then b then [c or d] then [d or c, whichever did not yet run] then e
    """
    # Start from this test
    self.test_dag_5node_acyclic_traversal_to_end()
    # Get traversal_list
    traversal_list = self.dag.traversal_list( [ "e" ] )
    self.assertEqual( len( traversal_list ), len( self.dag._nodes ) )

    expected = self.dag.traversal_to( [ "e" ] )
    self.validate_traversal( traversal_list, expected )

  def test_dag_multinode_entry_multinode_end_partial( self ):
    """A valid DAG consisting of multiple zero in-degree nodes

    This test will have multiple required in-degree nodes but also multiple
    ending nodes such that a traversal to one results in a partial traversal
    start -> stop
        b - d
    a <   /   > l => requires [a,f,i], [b,c,g], [d,e]
        c - e
    f <   /   > m => requires [a,f,i], [c,g,j], [e,h]
        g - h
    i <   /   > n => requires [f,i], [g,j], [h,k]
        j - k
    """
    self.dag.add_edge( "d", "l" )
    self.dag.add_edge( "e", "l" )
    self.dag.add_edge( "e", "m" )
    self.dag.add_edge( "h", "m" )
    self.dag.add_edge( "h", "n" )
    self.dag.add_edge( "k", "n" )

    self.dag.add_edge( "b", "d" )
    self.dag.add_edge( "c", "d" )
    self.dag.add_edge( "c", "e" )
    self.dag.add_edge( "g", "e" )
    self.dag.add_edge( "g", "h" )
    self.dag.add_edge( "j", "h" )
    self.dag.add_edge( "j", "k" )

    self.dag.add_edge( "a", "b" )
    self.dag.add_edge( "a", "c" )
    self.dag.add_edge( "f", "c" )
    self.dag.add_edge( "f", "g" )
    self.dag.add_edge( "i", "g" )
    self.dag.add_edge( "i", "j" )

    traversal_list = self.dag.traversal_list( [ "l" ] )
    self.assertNotEqual( len( traversal_list ), len( self.dag._nodes ) )

    expected = [ [ "a", "f", "i" ], [ "b", "c", "g" ], [ "d", "e" ], [ "l" ] ]
    self.validate_traversal( traversal_list, expected )

    traversal_list = self.dag.traversal_list( [ "m" ] )
    self.assertNotEqual( len( traversal_list ), len( self.dag._nodes ) )

    expected = [ [ "a", "f", "i" ], [ "c", "g", "j" ], [ "e", "h" ], [ "m" ] ]
    self.validate_traversal( traversal_list, expected )

    traversal_list = self.dag.traversal_list( [ "n" ] )
    self.assertNotEqual( len( traversal_list ), len( self.dag._nodes ) )

    expected = [ [ "f", "i" ], [ "g", "j" ], [ "h", "k" ], [ "n" ] ]
    self.validate_traversal( traversal_list, expected )

  def test_dag_traversal_backwards_compat( self ):
    """Test that traversal_to() with no start_nodes matches original behavior

    Ensures backward compatibility: traversal_to(nodes) == traversal_to(nodes, start_nodes=None)
    """
    self.test_dag_5node_acyclic_single_entry_single_end()

    traversal_to_result = self.dag.traversal_to( [ "e" ] )
    traversal_result = self.dag.traversal_to( [ "e" ], start_nodes=None )

    self.assertEqual( traversal_to_result, traversal_result )

  def test_dag_traversal_single_start_single_end( self ):
    """Test traversal with single start and single end node

    Simple linear path:
          a -> b -> c -> d
    """
    self.dag.add_edge( "a", "b" )
    self.dag.add_edge( "b", "c" )
    self.dag.add_edge( "c", "d" )

    # Traverse from a to d should include all nodes
    traversal = self.dag.traversal_to( [ "d" ], start_nodes=[ "a" ] )
    all_nodes = [ node for level in traversal for node in level ]
    self.assertEqual( all_nodes, [ "a", "b", "c", "d" ] )

    # Traverse from b to d should exclude a
    traversal = self.dag.traversal_to( [ "d" ], start_nodes=[ "b" ] )
    all_nodes = [ node for level in traversal for node in level ]
    self.assertEqual( all_nodes, [ "b", "c", "d" ] )

  def test_dag_traversal_diverge_converge( self ):
    """Test traversal on a diamond-shaped DAG

          a
          |
        __|__
      v      v
      b      c
      |______|
          |
          v
          d

    Traversing from a to d should include all nodes
    Traversing from b to d should only include b, d (no c)
    Traversing from c to d should only include c, d (no b)
    """
    self.dag.add_edge( "a", "b" )
    self.dag.add_edge( "a", "c" )
    self.dag.add_edge( "b", "d" )
    self.dag.add_edge( "c", "d" )

    # Full path
    traversal = self.dag.traversal_to( [ "d" ], start_nodes=[ "a" ] )
    all_nodes = [ node for level in traversal for node in level ]
    self.assertIn( "a", all_nodes )
    self.assertIn( "b", all_nodes )
    self.assertIn( "c", all_nodes )
    self.assertIn( "d", all_nodes )
    self.assertEqual( len( all_nodes ), 4 )

    # Only b branch
    traversal = self.dag.traversal_to( [ "d" ], start_nodes=[ "b" ] )
    all_nodes = [ node for level in traversal for node in level ]
    self.assertIn( "b", all_nodes )
    self.assertIn( "d", all_nodes )
    self.assertNotIn( "a", all_nodes )
    self.assertNotIn( "c", all_nodes )
    self.assertEqual( len( all_nodes ), 2 )

    # Only c branch
    traversal = self.dag.traversal_to( [ "d" ], start_nodes=[ "c" ] )
    all_nodes = [ node for level in traversal for node in level ]
    self.assertIn( "c", all_nodes )
    self.assertIn( "d", all_nodes )
    self.assertNotIn( "a", all_nodes )
    self.assertNotIn( "b", all_nodes )
    self.assertEqual( len( all_nodes ), 2 )

  def test_dag_traversal_multiple_starts( self ):
    """Test traversal with multiple start nodes pruning non-reachable paths

    This test demonstrates subgraph extraction when starting from multiple nodes
    and shows how unreachable paths are pruned from the result.

    DAG structure with paths and dead ends:

          a
         / \
        v   v
        b   c
        |  / \
        v v   v
        d e   f
         v    |
         l    v
              g

    where: a is root (in-degree 0)
           l is the target end node
           f->g is a dead end (doesn't reach l)

    Traversing from [a, c] to [l]:
    - Includes paths a->b->d->l and a->c->e->l (both reach l)
    - Excludes path c->f->g (dead end, doesn't reach l)
    - Result: [a, c, b, d, e, l] (not f, g)
    """
    # Setup the DAG with two reachable paths to l and one unreachable dead end
    self.dag.add_edge( "a", "b" )
    self.dag.add_edge( "a", "c" )
    self.dag.add_edge( "b", "d" )
    self.dag.add_edge( "d", "l" )
    self.dag.add_edge( "c", "e" )
    self.dag.add_edge( "e", "l" )
    self.dag.add_edge( "c", "f" )
    self.dag.add_edge( "f", "g" )  # Dead end: f->g doesn't reach l

    # From [a, c] to [l]: pruning dead-end branch (f->g)
    traversal = self.dag.traversal_to( [ "l" ], start_nodes=[ "a", "c" ] )
    all_nodes = [ node for level in traversal for node in level ]

    # Check expected nodes are present
    self.assertIn( "a", all_nodes )
    self.assertIn( "c", all_nodes )
    self.assertIn( "b", all_nodes )
    self.assertIn( "d", all_nodes )
    self.assertIn( "e", all_nodes )
    self.assertIn( "l", all_nodes )

    # Check that pruned nodes are not present
    self.assertNotIn( "f", all_nodes )
    self.assertNotIn( "g", all_nodes )
    self.assertEqual( len( all_nodes ), 6 )

  def test_dag_traversal_partial_start_nodes( self ):
    """Test subgraph traversal with only partial start nodes specified

    Using complex multinode structure, traverse from a subset of available
    root nodes to an end node, showing that nodes from excluded start paths
    are pruned from the result.
    """
    self.test_dag_multinode_entry_multinode_end_partial()

    # Full graph has roots [a, f, i] but we only traverse from [f, i]
    # Node a and its descendants that don't connect through f or i should be excluded
    traversal = self.dag.traversal_to( [ "m" ], start_nodes=[ "f", "i" ] )
    all_nodes = [ node for level in traversal for node in level ]

    # Should include f, i (starts) and m (end)
    self.assertIn( "f", all_nodes )
    self.assertIn( "i", all_nodes )
    self.assertIn( "m", all_nodes )

    # Intermediate nodes on paths from [f, i] to [m]
    self.assertIn( "c", all_nodes )  # f -> c
    self.assertIn( "g", all_nodes )  # f -> g and i -> g
    self.assertIn( "j", all_nodes )  # i -> j
    self.assertIn( "e", all_nodes )  # c -> e, g -> e
    self.assertIn( "h", all_nodes )  # g -> h, j -> h

    # Node a is not reachable from [f, i] so should not be present
    self.assertNotIn( "a", all_nodes )

    # Node b is reachable only through a, so should not be present
    self.assertNotIn( "b", all_nodes )
    self.assertNotIn( "d", all_nodes )

    # Node l is not an end point in this traversal
    self.assertNotIn( "l", all_nodes )

  def test_dag_traversal_intermediate_to_multiple_ends( self ):
    """Test subgraph traversal from intermediate node to multiple end nodes

    Using the complex multinode structure, start from intermediate node [c]
    and traverse to multiple end nodes [l, m], showing diverging lineages.

    This demonstrates that start nodes need not be root nodes (in-degree zero),
    and that the subgraph correctly includes all nodes on paths from start to ends.
    """
    self.test_dag_multinode_entry_multinode_end_partial()

    # Traverse from intermediate node [c] to [l, m]
    # c has in-degree 2 (from a, f) and out-degree 2 (to d, e)
    traversal = self.dag.traversal_to( [ "l", "m" ], start_nodes=[ "c" ] )
    all_nodes = [ node for level in traversal for node in level ]

    # Check that start node is present
    self.assertIn( "c", all_nodes )

    # Check that all end nodes are present
    self.assertIn( "l", all_nodes )
    self.assertIn( "m", all_nodes )

    # Check intermediate nodes on paths from c to [l, m]
    self.assertIn( "d", all_nodes )  # c -> d -> l
    self.assertIn( "e", all_nodes )  # c -> e -> l and c -> e -> m

    # h is NOT reachable from c (requires g which is not an ancestor of c)
    self.assertNotIn( "h", all_nodes )

    # Nodes not on any path from c to [l, m] should not be present
    self.assertNotIn( "a", all_nodes )
    self.assertNotIn( "b", all_nodes )
    self.assertNotIn( "f", all_nodes )
    self.assertNotIn( "g", all_nodes )
    self.assertNotIn( "i", all_nodes )
    self.assertNotIn( "j", all_nodes )
    self.assertNotIn( "k", all_nodes )
    self.assertNotIn( "n", all_nodes )

  def test_dag_traversal_intermediate_orphaned_end( self ):
    """Test subgraph traversal when one end node is unreachable from start

    Using the complex multinode structure, start from intermediate node [c]
    and traverse to [l, m, n]. Since n is unreachable from c (requires j and k
    which are not descendants of c), the function returns only the subgraph
    containing paths to the reachable end nodes l and m.

    This demonstrates that when multiple end nodes are specified but some are
    unreachable, the function returns paths to the reachable ones and excludes
    the unreachable nodes entirely from the result.
    """
    self.test_dag_multinode_entry_multinode_end_partial()

    # Traverse from [c] to [l, m, n]
    # l and m are reachable from c, but n requires j which is not reachable from c
    traversal = self.dag.traversal_to( [ "l", "m", "n" ], start_nodes=[ "c" ] )
    all_nodes = [ node for level in traversal for node in level ]

    # Should include c and the nodes on paths to l and m
    self.assertIn( "c", all_nodes )
    self.assertIn( "l", all_nodes )
    self.assertIn( "m", all_nodes )
    self.assertIn( "d", all_nodes )  # c -> d -> l
    self.assertIn( "e", all_nodes )  # c -> e -> l, m

    # n should NOT be in the result since it's unreachable from c
    self.assertNotIn( "n", all_nodes )
    # h, k, j, i are not on paths from c to [l, m]
    self.assertNotIn( "h", all_nodes )
    self.assertNotIn( "k", all_nodes )
    self.assertNotIn( "j", all_nodes )
    self.assertNotIn( "i", all_nodes )

  def test_dag_traversal_intermediate_with_diamond( self ):
    """Test subgraph traversal between intermediate nodes with diamond pattern

    Demonstrate that traversal_to correctly handles subgraphs containing
    diamond-shaped convergence patterns between intermediate start and end nodes.

    DAG structure:
        a
        |
        v
        b (intermediate start)
       / \
      v   v
      d   e
       \ /
        v
        f (intermediate end)
        |
        v
        g

    Starting from b (in-degree 1, out-degree 2) to f (in-degree 2, out-degree 1)
    should include the diamond [d, e] and their convergence at f.
    """
    self.dag.add_edge( "a", "b" )
    self.dag.add_edge( "b", "d" )
    self.dag.add_edge( "b", "e" )
    self.dag.add_edge( "d", "f" )
    self.dag.add_edge( "e", "f" )
    self.dag.add_edge( "f", "g" )

    # Traverse from b (intermediate) to f (also intermediate)
    traversal = self.dag.traversal_to( [ "f" ], start_nodes=[ "b" ] )
    all_nodes = [ node for level in traversal for node in level ]

    # Check that start and end are present
    self.assertIn( "b", all_nodes )
    self.assertIn( "f", all_nodes )

    # Check that both branches of the diamond are present
    self.assertIn( "d", all_nodes )
    self.assertIn( "e", all_nodes )

    # Nodes outside the subgraph should not appear
    self.assertNotIn( "a", all_nodes )  # ancestor of start
    self.assertNotIn( "g", all_nodes )  # descendant of end

    # Should have exactly 4 nodes: b, d, e, f
    self.assertEqual( len( all_nodes ), 4 )

    # Verify the structure has the diamond
    # Should have layers like [b], [d, e], [f]
    self.assertEqual( len( traversal ), 3 )  # 3 layers
    self.assertIn( "b", traversal[0] )
    self.assertIn( "d", traversal[1] )
    self.assertIn( "e", traversal[1] )
    self.assertIn( "f", traversal[2] )

  def test_dag_traversal_intermediate_to_intermediate( self ):
    """Test subgraph traversal between non-root and non-leaf nodes

    Demonstrate that traversal_to can return a subgraph for nodes that are
    neither true start (in-degree zero) nor true end (out-degree zero) nodes.

    Creates a simple path:
        a -> b -> c -> d

    Where b and c are both intermediate (in-degree > 0, out-degree > 0).
    Starting from b to c returns only the subgraph [b, c].
    """
    self.dag.add_edge( "a", "b" )
    self.dag.add_edge( "b", "c" )
    self.dag.add_edge( "c", "d" )

    # Traverse from b (intermediate) to c (also intermediate)
    # b has in-degree 1 (from a) and out-degree 1 (to c)
    # c has in-degree 1 (from b) and out-degree 1 (to d)
    traversal = self.dag.traversal_to( [ "c" ], start_nodes=[ "b" ] )
    all_nodes = [ node for level in traversal for node in level ]

    # Only b and c should be in the result
    self.assertIn( "b", all_nodes )
    self.assertIn( "c", all_nodes )

    # Nodes outside the subgraph should not appear
    self.assertNotIn( "a", all_nodes )  # ancestor
    self.assertNotIn( "d", all_nodes )  # descendant

    # Should only be 2 nodes
    self.assertEqual( len( all_nodes ), 2 )

  def test_dag_traversal_no_path( self ):
    """Test traversal when start nodes cannot reach end nodes

          a -> b

          c -> d

    Traversing from a to d should return empty (no path exists)
    """
    self.dag.add_edge( "a", "b" )
    self.dag.add_edge( "c", "d" )

    traversal = self.dag.traversal_to( [ "d" ], start_nodes=[ "a" ] )
    self.assertEqual( traversal, [] )

  def test_dag_traversal_start_equals_end( self ):
    """Test traversal when start node equals end node

    a -> b -> c

    Traversing from b to b should only include b
    """
    self.dag.add_edge( "a", "b" )
    self.dag.add_edge( "b", "c" )

    traversal = self.dag.traversal_to( [ "b" ], start_nodes=[ "b" ] )
    all_nodes = [ node for level in traversal for node in level ]
    self.assertEqual( all_nodes, [ "b" ] )

  def test_dag_visualize( self ):
    self.test_dag_multinode_entry_multinode_end_partial()
    print( dagvis( self.dag, [ "l", "m", "n" ] ) )
    self.dag.add_edge( 0, 1 )
    self.dag.add_edge( 0, 2 )
    self.dag.add_edge( 0, 4 )
    self.dag.add_edge( 1, 2 )
    self.dag.add_edge( 1, 3 )
    self.dag.add_edge( 1, 5 )
    self.dag.add_edge( 2, 3 )
    self.dag.add_edge( 2, 4 )
    print( dagvis( self.dag, [ 3, 4, 5 ] ) )
