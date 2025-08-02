import functools
import pickle

import sane.logger as logger
import sane.utdict as utdict
import sane.action as action
import sane.host as host


_registered_functions = {}


# https://stackoverflow.com/a/14412901
def callable_decorator( f ):
  '''
  a decorator decorator, allowing the decorator to be used as:
  @decorator(with, arguments, and=kwargs)
  or
  @decorator
  '''
  @functools.wraps( f )
  def insitu_decorator( *args, **kwargs ):
    if len( args ) == 1 and len( kwargs ) == 0 and callable( args[0] ):
      # actual decorated function
      return f( args[0] )
    else:
      # decorator arguments
      return lambda realf: f( realf, *args, **kwargs )

  return insitu_decorator


@callable_decorator
def register( f, priority=0 ):
  if priority not in _registered_functions:
    _registered_functions[priority] = []
  _registered_functions[priority].append( f )
  return f


class Orchestrator( logger.Logger ):
  def __init__( self ):
    self.actions = utdict.UniqueTypedDict( action.Action )
    self.hosts   = utdict.UniqueTypedDict( host.Host )

    self._dag    = dag.DAG()

    self._current_host  = None
    self._save_location = "./"
    self._working_directory = "./"

    super().__init__( "orchestrator" )

  def add_action( self, action ):
    self.actions[action.id] = action

  def add_host( self, host ):
    self.hosts[host.name] = host

  def construct_dag( self ):
    for id, action in self.actions.items():
      self._dag.add_node( id )
      for dependency in action.dependencies.keys():
        self._dag.add_edge( dependency, id )

    nodes, valid = self._dag.topological_sort()
    if not valid:
      msg = f"Error: In {Orchestrator.add_action.__name__}() DAG construction failed, invalid topology"
      self.log( msg )
      raise Exception( msg )

  def process_registered( self ):
    keys = sorted( registered_functions.keys() )
    for key in keys:
      for f in _registered_functions[key]:
        f( self )

  def check_hostenv( self, as_host, traversal_list ):
    for host_name, host in self.hosts.items():
      self.log( f"Checking host \"{host_name}\"" )
      if host.valid_host( as_host ):
        self._current_host = host_name
        break

    if self._current_host is None:
      self.log( "No valid host configuration found" )
      raise Exception( f"No valid host configuration found" )

    self.log( f"Running as {as_host}" )
    host = self.hosts[self._current_host]

    # Check action needs
    check_list = traversal_list.copy()
    missing_env = []
    while len( check_list ) > 0:
      next_nodes = self._dag.get_next_nodes( check_list )
      for node in next_nodes:
        env = host.has_environment( self.actions[node].environment )

        if env is None:
          env_name = self.actions[node].environment
          if self.actions[node].environment is None:
            env_name = "default"
          missing_env.append( ( node, env_name ) )

        self._dag.node_complete( node, check_list )

    if len( missing_env ) > 0:
      self.log( f"Error: Missing environments in Host( \"{self._current_host}\" )" )
      self.log_push()
      for node, env_name in missing_env:
        self.log( f"Action( \"{node}\" ) requires Environment( \"{env_name}\" )" )
      self.log_pop()
      raise Exception( f"Missing environments {missing_env}" )

  def run_actions( self, action_id_list, as_host=None ):
    self.construct_dag()

    traversal_list = self._dag.traversal_list( action_id_list )

    self.check_hostenv( as_host, traversal_list )

    # We have a valid host for all actions slated to run
    host_file = f"{self.save_location}/{self._current_host}.pkl"

    with open( host_file, "wb" ) as f:
      pickle.dump( self.hosts[self._current_host], f )

    while len( traversal_list ) > 0:
      next_nodes = self._dag.get_next_nodes( traversal_list )
      for node in next_nodes:
        self.actions[node].config["host_file"] = host_file

        # TODO Fix up pathing
        action_file = f"{self._save_location}/{node}.pkl"
        with open( action_file, "wb" ) as f:
          pickle.dump( self.actions[node], f )

        self.actions[node].launch( self._working_directory, action_file )
        self._dag.node_complete( node, traversal_list )
