from typing import Any
import functools
import importlib.util
import json
import os
import pathlib
import shutil
import sys
import threading
from concurrent.futures import ThreadPoolExecutor


import sane.action
import sane.dag as dag
import sane.host
import sane.hpc_host
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
  longest_action = len( max( action_list, key=len ) )
  max_line = 100
  n_per_line = int( max_line / longest_action )

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
    self.force_local = False

    self._dag    = dag.DAG()

    self._current_host  = None
    self._save_location = "./"
    self._log_location  = "./"
    self._filename      = "orchestrator.json"
    self._working_directory = "./"
    self._patch_configs = {}

    self.search_paths    = []
    self.search_patterns = []

    self.__searched__ = False
    self.__run_lock__ = threading.Lock()
    self.__wake__     = threading.Event()

    super().__init__( logname="orchestrator" )

  @property
  def working_directory( self ):
    return os.path.abspath( self._working_directory )

  @working_directory.setter
  def working_directory( self, path ):
    self._working_directory = path
    os.chdir( self._working_directory )

  @property
  def save_location( self ):
    return os.path.abspath( self._save_location )

  @save_location.setter
  def save_location( self, path ):
    self._save_location = path

  @property
  def log_location( self ):
    return os.path.abspath( self._log_location )

  @log_location.setter
  def log_location( self, path ):
    self._log_location = path

  @property
  def save_file( self ):
    return os.path.abspath( f"{self.save_location}/{self._filename}" )

  def add_action( self, action ):
    self.actions[action.id] = action

  def add_host( self, host ):
    self.hosts[host.name] = host

  @property
  def current_host( self ):
    return self._current_host

  def construct_dag( self ):
    for id, action in self.actions.items():
      self._dag.add_node( id )
      for dependency in action.dependencies.keys():
        self._dag.add_edge( dependency, id )

    nodes, valid = self._dag.topological_sort()
    if not valid:
      msg = f"Error: In {Orchestrator.construct_dag.__name__}() DAG construction failed, invalid topology"
      self.log( msg, level=50 )
      raise Exception( msg )

  def add_search_paths( self, search_paths ):
    if self.__searched__:
      self.log( "Paths already searched, adding paths later not supported", level=30 )
      return

    for search_path in search_paths:
      if search_path in self.search_paths:
        self.log( f"Search path already in search list : '{search_path}'", level=30 )
      else:
        self.search_paths.append( search_path )

  def add_search_patterns( self, search_patterns ):
    if self.__searched__:
      self.log( "Paths already searched, adding paths later not supported", level=30 )
      return

    for search_pattern in search_patterns:
      if search_pattern in self.search_patterns:
        self.log( f"Search pattern already in search pattern list : '{search_pattern}'", level=30 )
      else:
        self.search_patterns.append( search_pattern )

  def load_paths( self ):
    if self.__searched__:
      self.log( f"Already searched and loaded", level=30 )
      return

    for search_path in self.search_paths:
      sys.path.append( search_path )
      # paths are stored as absolute here since save state may need them as such
      uspace.user_paths.append( os.path.abspath( search_path ) )

    self.log( "Searching for workflow files..." )
    files = []
    for search_path in self.search_paths:
      for search_pattern in self.search_patterns:
        # Now search for each path each pattern
        self.log( f"  Searching {search_path} for {search_pattern}" )
        for path in pathlib.Path( search_path ).rglob( search_pattern ):
          self.log( f"    Found {path}" )
          files.append( path )

    files_sorted = {}
    for file in files:
      ext = file.suffix
      if ext not in files_sorted:
        files_sorted[ext] = []

      files_sorted[ext].append( file )

    # Do all python-based definitions first
    if ".py" in files_sorted:
      self.load_py_files( files_sorted[".py"] )

    self.process_registered()

    # Then finally do config files
    if ".json" in files_sorted:
      self.load_config_files( files_sorted[".json"] )

    if ".jsonc" in files_sorted:
      self.load_config_files( files_sorted[".jsonc"] )

    self.process_patches()
    self.__searched__ = True

  def process_registered( self ):
    # Higher number equals higher priority
    # this makes default registered generally go last
    self.push_logscope( "::register" )
    keys = sorted( _registered_functions.keys(), reverse=True )
    for key in keys:
      for f in _registered_functions[key]:
        f( self )
    self.pop_logscope()

  def process_patches( self ):
    # Higher number equals higher priority
    # this makes default registered generally go last
    self.push_logscope( "::patch" )
    keys = sorted( self._patch_configs.keys(), reverse=True )
    for key in keys:
      for patch in self._patch_configs[key]:
        hosts = patch.pop( "hosts", {} )
        for id, host_config in hosts.items():
          if id not in self.hosts:
            self.log( f"Host '{id}' does not exist, cannot patch", level=30 )
          else:
            self.log( f"Applying patch to Host '{id}'" )
            self.hosts[id].load_config( host_config )

        actions = patch.pop( "actions", {} )
        for id, action_config in actions.items():
          if id not in self.actions:
            self.log( f"Action '{id}' does not exist, cannot patch", level=30 )
          else:
            self.log( f"Applying patch to Action '{id}'" )
            self.actions[id].load_config( action_config )

        if len( patch ) > 0:
          self.log( f"Unused keys in patch : {list(patch.keys())}", level=30 )

    self.pop_logscope()

  def find_host( self, as_host ):
    for host_name, host in self.hosts.items():
      self.log( f"Checking host \"{host_name}\"" )
      if host.valid_host( as_host ):
        self._current_host = host_name
        break
    self.log( f"Running as '{self.current_host}'" )
    

    if self.current_host is None:
      self.log( "No valid host configuration found", level=50 )
      raise Exception( f"No valid host configuration found" )
    return self.current_host

  def check_host( self, traversal_list ):
    self.log( f"Checking ability to run all actions..." )
    host = self.hosts[self.current_host]
    self.log_push()
    host.log_push()

    # Check action needs
    check_list = traversal_list.copy()
    missing_env = []
    self.log( f"Checking environments..." )
    for node in traversal_list:
      env = host.has_environment( self.actions[node].environment )
      if env is None:
        env_name = self.actions[node].environment
        if self.actions[node].environment is None:
          env_name = "default"
        missing_env.append( ( node, env_name ) )

    if len( missing_env ) > 0:
      self.log( f"Missing environments in Host( \"{self.current_host}\" )", level=50 )
      self.log_push()
      for node, env_name in missing_env:
        self.log( f"Action( \"{node}\" ) requires Environment( \"{env_name}\" )", level=40 )
      self.log_pop()
      raise Exception( f"Missing environments {missing_env}" )

    runnable = True
    missing_resources = []
    self.log( f"Checking resource availability..." )
    host.log_push()
    for node in traversal_list:
      can_run = host.resources_available( self.actions[node].resources( host.name ), requestor=self.actions[node] )
      runnable = runnable and can_run
      if not can_run:
        missing_resources.append( node )
    host.log_pop()

    if not runnable:
      self.log( "Found Actions that would not be able to run due to resource limitations:", level=50 )
      self.log_push()
      print_actions( missing_resources, print=self.log )
      self.log_pop()
      raise Exception( f"Missing resources to run {missing_resources}" )

    self.log_pop()
    host.log_pop()
    self.log( "* " * 50 )
    self.log( "* " * 10 + "{0:^60}".format( f" All prerun checks for '{host.name}' passed " ) + "* " * 10 )
    self.log( "* " * 50 )

  def setup( self ):
    self.construct_dag()
    os.makedirs( self.save_location, exist_ok=True )
    os.makedirs( self.log_location, exist_ok=True )
    for name, action in self.actions.items():
      action._run_lock = self.__run_lock__
      action.__wake__  = self.__wake__

  def run_actions( self, action_id_list, as_host=None, skip_unrunnable=False ):
    # Setup does not take that long so make sure it is always run
    self.setup()

    for action in action_id_list:
      if action not in self.actions:
        msg = f"Action '{action}' does not exist in current workflow"
        self.log( msg, level=50 )
        raise KeyError( msg )

    self.log( "Running actions:" )
    print_actions( action_id_list, print=self.log )
    self.log( "and any necessary dependencies" )

    traversal_list = self._dag.traversal_list( action_id_list )
    self.log( "Full action set:" )
    action_set = list(traversal_list.keys())
    print_actions( action_set, print=self.log )

    self.find_host( as_host )
    self.check_host( traversal_list )

    # We have a valid host for all actions slated to run
    host = self.hosts[self.current_host]
    host.save_location = self.save_location
    host.dry_run = self.dry_run
    self.log( "Saving host information..." )
    host.save()

    self.log( "Setting state of all inactive actions to pending" )
    # Mark all actions to be run as pending if not already run
    for node in traversal_list:
      if self.actions[node].state == sane.action.ActionState.INACTIVE:
        self.actions[node].set_state_pending()

    self.save( action_set )
    next_nodes = []
    processed_nodes = []
    executor = ThreadPoolExecutor( max_workers=12, thread_name_prefix="thread" )
    results = {}
    self.log( f"Using working directory : '{self.working_directory}'" )

    host.pre_run_actions( { node : self.actions[node] for node in action_set } )

    self.log( "Running actions..." )
    while len( traversal_list ) > 0 or len( next_nodes ) > 0 or len( processed_nodes ) > 0:
      next_nodes.extend( self._dag.get_next_nodes( traversal_list ) )
      for node in next_nodes.copy():
        if self.actions[node].state == sane.action.ActionState.PENDING:
          # Gather all dependency nodes
          dependencies = { action_id : self.actions[action_id] for action_id in self.actions[node].dependencies.keys() }
          # Check requirements met
          requirements_met = False
          with self.__run_lock__:  # protect logs
            requirements_met = self.actions[node].requirements_met( dependencies )

          if requirements_met:
            resources_available = False
            with self.__run_lock__:  # protect logs
              resources_available = host.acquire_resources( self.actions[node].resources( host.name ), requestor=self.actions[node] )
            if resources_available:
              # Set info first
              self.actions[node].__host_info__ = host.info
              # if these are not set then default to action settings
              if self.verbose:
                self.actions[node].verbose = self.verbose
              if self.force_local:
                self.actions[node].local = self.force_local

              self.actions[node].dry_run = self.dry_run
              self.actions[node].save_location = self.save_location
              self.actions[node].log_location = self.log_location

              launch_wrapper = None
              with self.__run_lock__:  # protect logs
                launch_wrapper = host.launch_wrapper( self.actions[node], dependencies )

              self.log( f"Running '{node}' on '{host.name}'" )
              with self.__run_lock__:
                host.pre_launch( self.actions[node] )
              self.log_flush()
              results[node] = executor.submit(
                                              self.actions[node].launch,
                                              self.working_directory,
                                              launch_wrapper=launch_wrapper
                                              )
              next_nodes.remove( node )
              processed_nodes.append( node )
            else:
              self.log( "Not enough resources in host right now, continuing and retrying later", level=10 )
              continue

          else:
            self.log(
                      f"Unable to run Action '{node}', requirements not met",
                      level=40 - int(skip_unrunnable) * 10
                      )
            next_nodes.remove( node )
            processed_nodes.append( node )
            # Force evaluation
            self.__wake__.set()
        elif self.actions[node].state != sane.action.ActionState.RUNNING:
          msg  = "Action {0:<24} already has {{state, status}} ".format( f"'{node}'" )
          msg += f"{{{self.actions[node].state.value}, {self.actions[node].status.value}}}"
          self.log( msg )
          next_nodes.remove( node )
          processed_nodes.append( node )
          # Force evaluation even though nothing was done we may get new actions to run
          self.__wake__.set()

      # We submitted everything we could so now wait for at least one action to wake us
      self.__wake__.wait()
      self.__wake__.clear()
      for node in processed_nodes.copy():
        if node in results and results[node].done():
          try:
            retval, content = results[node].result()
            host.post_launch( self.actions[node], retval, content )
            # Regardless, return resources
            host.release_resources( self.actions[node].resources( host.name ), requestor=self.actions[node] )
            del results[node]
          except Exception as e:
            for k, v in results.items():
              v.cancel()
            executor.shutdown( wait=True )
            raise e

        run_state = sane.action.ActionState.valid_run_state( self.actions[node].state )
        if ( self.actions[node].state == sane.action.ActionState.FINISHED
           or ( skip_unrunnable and not run_state ) ):
          msg  = "{{state}} Action {0:<24} completed with '{{status}}'".format( f"'{node}'" )
          msg  = msg.format( state=self.actions[node].state.value.upper(), status=self.actions[node].status.value )
          self.log( msg )
          self._dag.node_complete( node, traversal_list )
          processed_nodes.remove( node )
        elif not run_state:
          # If we get here, we DO want to error
          msg = f"Action '{node}' did not return finished state : {self.actions[node].state.value}"
          self.log( msg, level=50 )
          raise Exception( msg )

        # We are in a good spot to save
        self.save( action_set )

    host.post_run_actions( { node : self.actions[node] for node in action_set } )

    self.log( "Finished running queued actions" )
    # Report final statuses
    longest_action = len( max( action_set, key=len ) )
    statuses = [ f"{node:<{longest_action}}: " + self.actions[node].status.value for node in action_set ]
    print_actions( statuses, print=self.log )
    status = all( [ self.actions[node].status == sane.action.ActionStatus.SUCCESS for node in action_set ] )
    if status:
      self.log( "All actions finished with success" )
    else:
      self.log( "Not all actions finished with success" )
    self.save( action_set )
    return status

  def load_py_files( self, files, parent=None ):
    for file in files:
      if not isinstance( file, pathlib.Path ):
        path_file = pathlib.Path( file ).relative_to( self.working_directory )
      else:
        path_file = file

      # Find search path that yielded this file if possible
      module_file = path_file
      for search_path in self.search_paths:
        if path_file.is_relative_to( search_path ):
          module_file = path_file.relative_to( search_path )
          break

      # Now load the file as is
      module_name = ".".join( module_file.parts ).rpartition( ".py" )[0]

      if not path_file.is_file():
        msg = f"Dynamic import of '{module_name}' not possible, file '{file}' does not exist"
        self.log( msg, level=50 )
        raise FileNotFoundError( msg )

      self.log( f"Loading python file {file} as '{module_name}'" )
      uspace.user_modules[module_name] = importlib.import_module( module_name )

  def load_config_files( self, files ):
    for file in files:
      self.log( f"Loading config file {file}")
      if not isinstance( file, pathlib.Path ):
        file = pathlib.Path( file )

      with open( file, "r" ) as fp:
        config = json.load( fp, cls=JSONCDecoder )
        self.log_push()
        self.load_config( config )
        self.log_pop()

  def load_core_config( self, config ):
    hosts = config.pop( "hosts", {} )
    for id, host_config in hosts.items():
      host_typename = host_config.pop( "type", sane.host.Host.CONFIG_TYPE )
      host_type = sane.host.Host
      if host_typename == sane.hpc_host.PBSHost.CONFIG_TYPE:
        host_type = sane.hpc_host.PBSHost
      elif host_typename != sane.host.Host.CONFIG_TYPE:
        host_type = self.search_type( host_typename )

      host = host_type( id )
      host.log_push()
      host.load_config( host_config )
      host.log_pop()

      self.add_host( host )

    actions = config.pop( "actions", {} )
    for id, action_config in actions.items():
      action_typename = action_config.pop( "type", sane.action.Action.CONFIG_TYPE )
      action_type = sane.action.Action
      if action_typename != sane.action.Action.CONFIG_TYPE:
        action_type = self.search_type( action_typename )
      action = action_type( id )
      action.log_push()
      action.load_config( action_config )
      action.log_pop()

      self.add_action( action )

    # Handle very similar to the register functions, including priority
    patches = config.pop( "patches", {} )
    priority = patches.pop( "priority", 0 )
    if priority not in self._patch_configs:
      self._patch_configs[priority] = []
    self._patch_configs[priority].append( patches )

  def _load_save_dict( self ):
    save_dict = {}
    if not os.path.isfile( self.save_file ):
      self.log( "No previous save file to load" )
      return {}

    try:
      with open( self.save_file, "r" ) as f:
        save_dict = json.load( f, cls=JSONCDecoder )
    except Exception as e:
      self.log( f"Could not open {self.save_file}", level=50 )
      raise e
    return save_dict

  def save( self, action_id_list ):
    # Only save current session changes
    save_dict = self._load_save_dict()
    save_dict_update = {
                        "actions" :
                        {
                          action :
                          {
                            "state"  : self.actions[action].state.value,
                            "status" : self.actions[action].status.value
                          } for action in action_id_list
                        },
                        "dry_run" : self.dry_run,
                        "verbose" : self.verbose,
                        "host" : self.current_host,
                        "save_location" : self.save_location,
                        "log_location" : self.log_location,
                        "working_directory" : self.working_directory
                      }
    save_dict = jconfig.recursive_update( save_dict, save_dict_update )
    with open( self.save_file, "w" ) as f:
      json.dump( save_dict, f, indent=2 )

  def load( self, clear_errors=True, clear_failures=True ):
    save_dict = self._load_save_dict()
    if not save_dict:
      return
    self.log( f"Loading save file {self.save_file}" )

    self.dry_run = save_dict["dry_run"]
    self.verbose = save_dict["verbose"]

    self._current_host = save_dict["host"]

    self.save_location = save_dict["save_location"]
    self.log_location = save_dict["log_location"]
    self.working_directory = save_dict["working_directory"]

    for action, action_dict in save_dict["actions"].items():
      state  = sane.action.ActionState(action_dict["state"])
      status = sane.action.ActionStatus(action_dict["status"])

      if action not in self.actions:
        tmp = self.save_file + ".backup"
        self.log( f"Loaded action info '{action}' missing from loaded workflow, state will be lost", level=40 )
        self.log( f"Making a copy of previous save file at '{tmp}'", level=40 )
        shutil.copy2( self.save_file, tmp )
        continue

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
