import functools
import pickle

import dag
import UniqueTypedDict as utd
from Action import *
from Host import *
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
    self.actions = utd.UniqueTypedDict( Action )
    self.hosts   = utd.UniqueTypedDict( Host )

    self.dag_    = dag.DAG()

    self.current_host_  = None
    self.save_location_ = "./"
    self.working_directory_ = "./"

    super().__init__( "orchestrator" )

  def add_action( self, action ):
    self.actions[action.id_] = action

  def add_host( self, host ):
    self.hosts[host.name_] = host

  def construct_dag( self ):
    for id, action in self.actions.items():
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

  def check_hostenv( self, as_host, traversal_list ):
    for host_name, host in self.hosts.items():
      self.log( f"Checking host \"{host_name}\"" )
      if host.valid_host( as_host ):
        self.current_host_ = host_name
        break

    if self.current_host_ is None:
      self.log( "No valid host configuration found" )
      raise Exception( f"No valid host configuration found" )

    self.log( f"Running as {as_host}" )
    host = self.hosts[self.current_host_]

    # Check action needs
    check_list = traversal_list.copy()
    missing_env = []
    while len( check_list ) > 0:
      next_nodes = self.dag_.get_next_nodes( check_list )
      for node in next_nodes:
        env_name = "default"
        found    = False
        env      = None

        if self.actions[node].environment_ is None:
          found, env = host.default_env()
        else:
          found, env = host.has_environment( self.actions[node].environment_ )

        if not found:
          missing_env.append( ( node, env_name ) )

        self.dag_.node_complete( node, check_list )

    if len( missing_env ) > 0:
      self.log( f"Error: Missing environments in Host( \"{self.current_host_}\" )" )
      self.log_push()
      for node, env_name in missing_env:
        self.log( f"Action( \"{node}\" ) requires Environment( \"{env_name}\" )" )
      self.log_pop()
      raise Exception( f"Missing environments {missing_env}" )


  def run_actions( self, action_id_list, as_host=None ):
    self.construct_dag()

    traversal_list = self.dag_.traversal_list( action_id_list )

    self.check_hostenv( as_host, traversal_list )
    
    # We have a valid host for all actions slated to run
    host_file = f"{self.save_location_}/{self.current_host_}.pkl"

    with open( host_file, "wb" ) as f:
      pickle.dump( self.hosts[self.current_host_], f )

    while len( traversal_list ) > 0:
      next_nodes = self.dag_.get_next_nodes( traversal_list )
      for node in next_nodes:
        self.actions[node].config_["host_file"] = host_file
        
        action_file = f"{self.save_location_}/{node}.pkl"
        with open( action_file, "wb" ) as f:
          pickle.dump( self.actions[node], f )

        self.actions[node].launch( self.working_directory_, action_file )
        self.dag_.node_complete( node, traversal_list )

