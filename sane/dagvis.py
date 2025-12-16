from sane.dag import DAG


def visualize( dag : DAG, nodes, align=False ):
  traversal_list = dag.traversal_list( nodes )
  # Connections
  # p =  |  pass
  # b =  L  bend
  # a =  _  across
  # t = _|_ t intersection end
  # c =  +  cross
  # s =  |- t intersection straight
  # o = -|- overpass
  # e =  *  end
  # n = ' ' null

  def rindex_with_children( nodes_ordered, visited ):
    for node in reversed( nodes_ordered ):
      children = dag._nodes[node]
      all_visited = []
      for child in children:
        if child in traversal_list and child not in visited:
          # We still need to visit this child in this traversal and it isn't the next node
          all_visited.append( False )
        else:
          all_visited.append( True )
      if len( all_visited ) > 0 and not all( all_visited ):
        # If we got here this is the first occurence of a node that has not
        # fully visited its children so use this index
        return nodes_ordered.index( node )
    # All checked nodes are okay so just go to the beginning
    return -1

  not_visited = traversal_list.copy()

  rows = [ ([], []) ]
  node_rows = {}
  node_cols = {}
  while len( not_visited ) > 0:
    next_nodes = dag.get_next_nodes( not_visited )
    for node in next_nodes:
      # Previous row
      col_nodes = rows[-1][0]
      col_chars = rows[-1][1]

      # Go from leftmost to the rightmost column of all direct parents and then find last available column
      parents = dag._rnodes[node]
      indexes = [ node_cols[p] for p in parents ]
      last_c  = rindex_with_children( col_nodes, node_rows.keys() )
      first_p = min( indexes, default=len(dag._nodes) )
      curr_nodes = col_nodes[:last_c + 1].copy()
      curr_chars = [ "a" if i > first_p else "n" for i, char in enumerate( col_chars[:last_c + 1] ) ]

      # Now for each direct parent go up the rows and ensure we are connectd
      for pidx, p in zip( indexes, parents ):
        for r in range( node_rows[p] + 1, len( rows ) ):
          pchar = rows[r][1][pidx]
          if pchar == "b":
            pchar = "s"
          elif pchar == "a":
            pchar = "o"
          elif pchar == "t":
            pchar = "c"
          elif pchar in [ "p", "c", "s", "o" ]:
            # Already connected down
            pass
          else:
            pchar = "p"
          rows[r][1][pidx] = pchar
        # Adjust current row to now intersect
        if pidx == first_p:
          curr_chars[pidx] = "b"
        else:
          curr_chars[pidx] = "t"

      # Next, insert our node at the very end of this
      curr_chars.append( "e" )
      curr_nodes.append( node )
      node_rows[node] = len( rows )
      node_cols[node] = len( curr_nodes ) - 1
      # Finally add this to the rows
      rows.append( ( curr_nodes, curr_chars ) )
      dag.node_complete( node, not_visited )

  output = ""
  max_cols = 0
  max_node = 0
  if align:
    max_cols = len( max( rows, key=lambda r: len(r[0]) )[0] )
    max_node = len( str( max( traversal_list.keys(), key=lambda n: len(str(n)) ) ) )

  for rcols, rchar in rows:
    line = ""
    for node, char in zip( rcols, rchar ):
      if char == "p":
        line += u"│ "
      elif char == "b":
        line += u"┗➢" # u"└─"
      elif char == "a":
        line += u"╌╌"
      elif char == "t":
        line += u"┺➢" #u"┴─"
      elif char == "c":
        line += u"╄➢" #u"╀─" # u"┼─"
      elif char == "s":
        line += u"┡➢" #u"├─"
      elif char == "o":
        line += u"│╌"
      elif char == "n":
        line += u"  "
      elif char == "e":
        line += u"•"
        line = f"{line:⋅<{max_cols*2}} {node}"
        if node in nodes:
          line += " " * ( max_node - len(str(node)) ) + u" ✧"
    output += line + "\n"
  return output
