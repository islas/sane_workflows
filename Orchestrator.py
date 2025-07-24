import functools

import dag
from Action import *
from Logger import *

registered_functions = {}
# https://stackoverflow.com/a/14412901
def callable_decorator( f ):
  '''
  a decorator decorator, allowing the decorator to be used as:
  @decorator(with, arguments, and=kwargs)
  or
  @decorator
  '''
  @functools.wraps(f)
  def insitu_decorator(*args, **kwargs):
    if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
      # actual decorated function
      return f(args[0])
    else:
      # decorator arguments
      return lambda realf: f(realf, *args, **kwargs)

  return insitu_decorator

@callable_decorator
def register( f, priority=0 ):
  if priority not in registered_functions:
    registered_functions[priority] = []
  registered_functions[priority] = f
  return f


class Orchestrator( Logger ):
  def __init__( self ):
    self.actions_ = {}
    self.dag_     = dag.DAG()
    super().__init__( "orchestrator" )

  def add_action( self, action ):
    if not isinstance( action, Action ):
      msg = f"Error: Provided Action to {Orchestrator.add_action.__name__}() is not of type Action"
      self.log( msg )
      raise Exception( msg )

    # We know we have an action type
    if action.id_ not in self.actions_:
      self.actions_[action.id_] = action
    else:
      msg = f"Error: Provided Action( \"{action.id_}\" ) to {Orchestrator.add_action.__name__}() does not have a unique ID"
      self.log( msg )
      raise Exception( msg )

    # defer creation of DAG dependency mapping until the very end

  def construct_dag( self ):
    for id, action in self.actions_.items():
      self.dag_.add_node( id )
      for dependency in action.dependencies_.keys():
        self.dag_.add_edge( dependency, id )
    
    nodes, valid = self.dag_.topological_sort()
    if not valid:
      msg = f"Error: In {Orchestrator.add_action.__name__}() DAG construction failed, invalid topology"
      self.log( msg )
      raise Exception( msg )
    
  def process_registered( self ):
    keys = sorted( registered_functions.keys() )
    for key in keys:
      registered_functions[key]( self )
  
  def run_actions( self, action_id_list ):
    self.construct_dag()

    traversal_list = self.dag_.traversal_list( action_id_list )

    while len( traversal_list ) > 0:
      next_nodes = self.dag_.get_next_nodes( traversal_list )
      for node in next_nodes:
        self.actions_[node].launch()
        self.dag_.node_complete( node, traversal_list )

