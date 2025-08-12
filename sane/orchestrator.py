from typing import Any
import functools
import importlib.util
import json
import os
import pathlib
import pickle
import sys


import sane.action
import sane.dag as dag
import sane.host
import sane.json_config as jconfig
import sane.user_space as uspace
import sane.utdict as utdict


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


def print_actions( action_list, n_per_line=4, print=print ):
  n_per_line = 4
  longest_action = len( max( action_list, key=len ) )
  for i in range( 0, int( len( action_list ) / n_per_line ) + 1 ):
    line = "  "
    for j in range( n_per_line ):
      if ( j + i * n_per_line ) < len( action_list ):
        line += f"{{0:<{longest_action + 2}}}".format( action_list[j + i * n_per_line] )
    if not line.isspace():
      print( line )


# https://stackoverflow.com/a/72168909
class JSONCDecoder( json.JSONDecoder ):
  def __init__( self, **kw ) :
    super().__init__( **kw )

  def decode( self, s : str ) -> Any :
    # Sanitize the input string for leading // comments ONLY and replace with
    # blank line so that line numbers are preserved
    s = '\n'.join( line if not line.lstrip().startswith( "//" ) else "" for line in s.split( '\n' ) )
    return super().decode( s )


class Orchestrator( jconfig.JSONConfig ):
  def __init__( self ):
    self.actions = utdict.UniqueTypedDict( sane.action.Action )
    self.hosts   = utdict.UniqueTypedDict( sane.host.Host )
    self.dry_run = False
    self.verbose = False

    self._dag    = dag.DAG()

    self._current_host  = None
    self._save_location = "./"
    self._filename      = "orchestrator.json"
    self._working_directory = "./"

    super().__init__( name="orchestrator" )

  @property
  def working_directory( self ):
    return os.path.abspath( self._working_directory )

  @working_directory.setter
  def working_directory( self, path ):
    self._working_directory = path

  @property
  def save_location( self ):
    return os.path.abspath( self._save_location )

  @save_location.setter
  def save_location( self, path ):
    self._save_location = path

  @property
  def save_file( self ):
    return os.path.abspath( f"{self.save_location}/{self._filename}" )

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
      msg = f"Error: In {Orchestrator.construct_dag.__name__}() DAG construction failed, invalid topology"
      self.log( msg )
      raise Exception( msg )

  def process_registered( self ):
    # Higher number equals higher priority
    # this makes default registered generally go last
    self.override_logname( f"{self.logname}::register" )
    keys = sorted( _registered_functions.keys(), reverse=True )
    for key in keys:
      for f in _registered_functions[key]:
        f( self )
    self.restore_logname()

  def check_hostenv( self, as_host, traversal_list ):
    for host_name, host in self.hosts.items():
      self.log( f"Checking host \"{host_name}\"" )
      if host.valid_host( as_host ):
        self._current_host = host_name
        break

    if self._current_host is None:
      self.log( "No valid host configuration found" )
      raise Exception( f"No valid host configuration found" )

    self.log( f"Running as {self._current_host}" )
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

  def run_actions( self, action_id_list, as_host=None, skip_unrunnable=False ):
    self.log( "Running actions:" )
    print_actions( action_id_list, print=self.log )
    self.log( "and any necessary dependencies" )

    self.construct_dag()

    traversal_list = self._dag.traversal_list( action_id_list )

    self.check_hostenv( as_host, traversal_list )

    os.makedirs( self.save_location, exist_ok=True )

    # We have a valid host for all actions slated to run
    self.hosts[self._current_host].save_location = self.save_location
    self.hosts[self._current_host].save()

    # Mark all actions to be run as pending if not already run
    for node in traversal_list:
      if self.actions[node].state == sane.action.ActionState.INACTIVE:
        self.actions[node].set_state_pending()

    while len( traversal_list ) > 0:
      next_nodes = self._dag.get_next_nodes( traversal_list )
      for node in next_nodes:
        if self.actions[node].state == sane.action.ActionState.PENDING:
          # Gather all dependency nodes
          dependencies = { action_id : self.actions[action_id] for action_id in self.actions[node].dependencies.keys() }
          # Check requirements met
          if self.actions[node].requirements_met( dependencies ):
            self.actions[node].config["host_file"] = self.hosts[self._current_host].save_file
            self.actions[node].verbose = self.verbose
            self.actions[node].dry_run = self.dry_run
            self.actions[node].save_location = self.save_location
            self.actions[node].save()
            self.actions[node].launch( self._working_directory )
          else:
            self.log(
                      f"Unable to run Action '{node}', requirements not met",
                      level=40 - int(skip_unrunnable) * 10
                      )
        else:
          self.log( f"Action '{node}' already has {{state, status}} {{{self.actions[node].state.value}, {self.actions[node].status.value}}}")

        if self.actions[node].state == sane.action.ActionState.FINISHED or skip_unrunnable:
          self._dag.node_complete( node, traversal_list )
        else:
          # If we get here, we DO want to error
          msg = f"Action {node} did not return finished state"
          self.log( msg, level=50 )
          raise Exception( msg )

  def load_py_files( self, files ):
    for file in files:
      self.log( f"Loading python file {file}")
      if not isinstance( file, pathlib.Path ):
        file = pathlib.Path( file )

      module_name = file.stem
      spec = importlib.util.spec_from_file_location( module_name, file.absolute() )
      user_module = importlib.util.module_from_spec( spec )
      sys.modules[module_name] = user_module
      spec.loader.exec_module( user_module )
      uspace.loaded_modules[module_name] = user_module

  def load_config_files( self, files ):
    for file in files:
      self.log( f"Loading config file {file}")
      if not isinstance( file, pathlib.Path ):
        file = pathlib.Path( file )

      with open( file, "r" ) as fp:
        config = json.load( fp, cls=JSONCDecoder )
        self.load_config( config )

  def load_core_config( self, config ):
    hosts = config.pop( "hosts", {} )
    for id, host_config in hosts.items():
      host_typename = host_config.pop( "type", sane.host.Host.CONFIG_TYPE )
      host_type = sane.host.Host
      if host_typename == sane.host.Host.CONFIG_TYPE:
        host_type = self.search_type( host_typename )

      host = host_type( id )
      host.load_config( host_config )

      self.add_host( host )

    actions = config.pop( "actions", {} )
    for id, action_config in actions.items():
      action_typename = action_config.pop( "type", sane.action.Action.CONFIG_TYPE )
      action_type = sane.action.Action
      if action_typename != sane.action.Action.CONFIG_TYPE:
        action_type = self.search_type( action_typename )
      action = action_type( id )
      action.load_config( action_config )

      self.add_action( action )

  def save( self ):
    save_dict = {
                  "actions" :
                  {
                    action.id :
                    {
                      "state"  : action.state.value,
                      "status" : action.status.value
                    } for id, action in self.actions.items()
                  },
                  "dry_run" : self.dry_run,
                  "verbose" : self.verbose,
                  "host" : self._current_host,
                  "save_location" : self.save_location,
                  "working_directory" : self.working_directory
                }
    with open( self.save_file, "w" ) as f:
      json.dump( save_dict, f, indent=2 )

  def load( self, clear_errors=True, clear_failures=True ):
    if not os.path.isfile( self.save_file ):
      self.log( "No previous save file to load" )
      return
    else:
      self.log( f"Loading save file {self.save_file}" )

    save_dict = {}
    try:
      with open( self.save_file, "r" ) as f:
        save_dict = json.load( f, cls=JSONCDecoder )
    except Exception as e:
      self.log( f"Could not open {self.save_file}", level=50 )
      raise e

    self.dry_run = save_dict["dry_run"]
    self.verbose = save_dict["verbose"]

    self._current_host = save_dict["host"]

    self.save_location = save_dict["save_location"]
    self.working_directory = save_dict["working_directory"]

    for action, action_dict in save_dict["actions"].items():
      state  = sane.action.ActionState(action_dict["state"])
      status = sane.action.ActionStatus(action_dict["status"])

      # THIS IS THE ONLY TIME WE SHOULD EVERY DIRECTLY SET STATUS/STATE
      self.actions[action]._state = state
      self.actions[action]._status = status

      if (
          # We never finished so reset
             ( state == sane.action.ActionState.RUNNING )
          # We would like to re-attempt
          or ( clear_errors and state == sane.action.ActionState.ERROR )
          or ( clear_failures and status == sane.action.ActionStatus.FAILURE )
          ):
        self.actions[action].set_state_pending()
