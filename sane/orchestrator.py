from typing import Any
import functools
import importlib.util
import json
import os
import pathlib
import shutil
import sys
import threading
import re
from concurrent.futures import ThreadPoolExecutor
import xml.etree.ElementTree as xmltree
import xml.dom.minidom


import sane.action
import sane.dag as dag
import sane.dagvis as dagvis
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

  @property
  def results_file( self ):
    return os.path.abspath( f"{self.log_location}/results.xml" )

  def add_action( self, action ):
    self.actions[action.id] = action

  def add_host( self, host ):
    self.hosts[host.name] = host

  @property
  def current_host( self ):
    return self._current_host

  def traversal_list( self, action_id_list ):
    self.construct_dag()
    return self._dag.traversal_list( action_id_list )

  def construct_dag( self ):
    self._dag.clear()

    for id, action in self.actions.items():
      self._dag.add_node( id )
      for dependency in action.dependencies.keys():
        self._dag.add_edge( dependency, id )

    nodes, valid = self._dag.topological_sort()
    if not valid:
      msg = f"Error: In {Orchestrator.construct_dag.__name__}() DAG construction failed, invalid topology"
      self.log( msg, level=50 )
      raise Exception( msg )

  def print_actions( self, action_id_list, visualize=False ):
    print_actions( action_id_list, print=self.log )
    if visualize:
      output = dagvis.visualize( self._dag, action_id_list )
      self.log( "" )
      self.log( "Action Graph:" )
      self.log_push()
      for line in output.splitlines()[1:]:
        self.log( line )
      self.log_pop()

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
      sys.path.insert( 0, search_path )
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
      for origin, patch in self._patch_configs[key].items():
        self.log( f"Processing patches from {origin}" )
        self.log_push()
        # go through patches in priority order then apply hosts then actions, respectively
        for pop_key, gentype, source in ( ( "hosts", "Host", self.hosts ), ( "actions", "Action", self.actions ) ):
          patch_dicts = patch.pop( pop_key, {} )
          for id, config in patch_dicts.items():
            if id in source:
              self.log( f"Applying patch to {gentype} '{id}'" )
              source[id].load_config( config.copy(), origin )
            elif id.startswith( "[" ) and id.endswith( "]" ):
              filter_ids = list( filter( lambda source_id: re.search( id[1:-1], source_id ), source.keys() ) )
              if len( filter_ids ) > 0:
                self.log( f"Applying patch filter '{id[1:-1]}' to [{len(filter_ids)}] {gentype}s" )
                for filter_id in filter_ids:
                  self.log( f"Applying patch filter to {gentype} '{filter_id}'", level=15 )
                  source[filter_id].load_config( config.copy(), origin )
              else:
                self.log( f"No {gentype} matches patch filter '{id[1:-1]}', cannot apply patch", level=30 )
            else:
              self.log( f"{gentype} '{id}' does not exist, cannot patch", level=30 )

        if len( patch ) > 0:
          self.log( f"Unused keys in patch : {list(patch.keys())}", level=30 )
        self.log_pop()

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
    self.log( f"Checking ability to run all actions on '{self.current_host}'..." )
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
    os.makedirs( self.save_location, exist_ok=True )
    os.makedirs( self.log_location, exist_ok=True )
    for name, action in self.actions.items():
      action._run_lock = self.__run_lock__
      action.__wake__  = self.__wake__

  def check_action_id_list( self, action_id_list ):
    for action in action_id_list:
      if action not in self.actions:
        msg = f"Action '{action}' does not exist in current workflow"
        self.log( msg, level=50 )
        raise KeyError( msg )

  def run_actions( self, action_id_list, as_host=None, skip_unrunnable=True, visualize=False ):
    # Setup does not take that long so make sure it is always run
    self.setup()
    self.check_action_id_list( action_id_list )
    self.log( "Running actions:" )
    self.print_actions( action_id_list )
    self.log( "and any necessary dependencies" )

    traversal_list = self.traversal_list( action_id_list )
    self.log( "Full action set:" )
    action_set = list(traversal_list.keys())
    if visualize:
      self.print_actions( action_id_list, visualize=visualize )
    else:
      self.print_actions( action_set )
    self.check_action_id_list( action_set )

    self.find_host( as_host )
    host = self.hosts[self.current_host]

    if isinstance( host, sane.resources.NonLocalProvider ):
      host.force_local = self.force_local

    self.check_host( traversal_list )

    # We have a valid host for all actions slated to run
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
    already_logged = []
    self.log( f"Using working directory : '{self.working_directory}'" )

    host.__wake__ = self.__wake__
    host_watchdog   = host.watchdog_func
    host_wd_results = None
    if host_watchdog is not None:
      self.log( f"Launching Host '{host.name}' watchdog function" )
      host_wd_results = executor.submit( host_watchdog, { node : self.actions[node] for node in action_set } )

    host.pre_run_actions( { node : self.actions[node] for node in action_set } )

    self.log( "Running actions..." )
    while len( traversal_list ) > 0 or len( next_nodes ) > 0 or len( processed_nodes ) > 0:
      try:
        next_nodes.extend( self._dag.get_next_nodes( traversal_list ) )
        for node in next_nodes.copy():
          if self.actions[node].state == sane.action.ActionState.PENDING:
            # Gather all dependency nodes
            dependencies = { action_id : self.actions[action_id] for action_id in self.actions[node].dependencies.keys() }
            # Check requirements met
            requirements_met = sane.action.RequirementsState.UNMET
            with self.__run_lock__:  # protect logs
              requirements_met = self.actions[node].requirements_met(
                                                                      dependencies,
                                                                      not isinstance(
                                                                        host,
                                                                        sane.resources.NonLocalProvider
                                                                        ) or host.launch_local( self.actions[node] )
                                                                      )

            if requirements_met == sane.action.RequirementsState.MET:
              resources_available = False
              with self.__run_lock__:  # protect logs
                resources_available = host.acquire_resources(
                                                              self.actions[node].resources( host.name ),
                                                              requestor=self.actions[node]
                                                              )
              if resources_available:
                # Set info first
                self.actions[node].__host_info__ = host.info
                jconfig.recursive_update( self.actions[node]._dependencies, { id : dep_action.info for id, dep_action in dependencies.items() } )
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
            elif requirements_met == sane.action.RequirementsState.PENDING:
              # We don't want this suppressed but also not constantly repeating
              if node not in already_logged:
                self.log( f"Waiting on Action '{node}' requirements to be met..." )
                already_logged.append( node )
              continue
            else:
              self.log(
                        f"Unable to run Action '{node}', requirements not met",
                        level=40 - int(skip_unrunnable) * 10
                        )
              next_nodes.remove( node )
              processed_nodes.append( node )
              # Force evaluation and set to no longer run
              self.actions[node].set_status_skipped()
              self.__wake__.set()
          elif self.actions[node].state != sane.action.ActionState.RUNNING:
            msg  = "Action {0:<24} already has {{state, status}} ".format( f"'{node}'" )
            msg += f"{{{self.actions[node].state.value}, {self.actions[node].status.value}}}"
            self.log( msg )
            next_nodes.remove( node )
            processed_nodes.append( node )
            # Force evaluation even though nothing was done we may get new actions to run
            self.__wake__.set()

      except Exception as e:
        # Bad things happened :(
        if self.__run_lock__.locked():
          self.__run_lock__.release()
        self.__wake__.set()
        host.kill_watchdog = True
        raise e

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
            host.kill_watchdog = True
            for k, v in results.items():
              v.cancel()
            executor.shutdown( wait=True )
            raise e

        run_state = sane.action.ActionState.valid_run_state( self.actions[node].state )
        if ( self.actions[node].state == sane.action.ActionState.FINISHED
           or ( skip_unrunnable and not run_state ) ):
          msg  = "[{{state:<8}}] ** Action {0:<24} completed with '{{status}}'".format( f"'{node}'" )
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

    # Shutdown workflow
    host.kill_watchdog = True
    executor.shutdown( wait=True )

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
    self.log( f"Save file at {self.save_file}" )
    self.save( action_set )
    self.log( f"JUnit file at {self.results_file}" )
    self.save_junit()
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
        sp_resloved = pathlib.Path( search_path ).resolve()
        if os.path.commonpath( [path_file.resolve(), sp_resloved] ) == str(sp_resloved):
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
        self.load_config( config, file )
        self.log_pop()

  def load_core_config( self, config, origin ):
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
      host.load_config( host_config, origin )
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
      action.load_config( action_config, origin )
      action.log_pop()

      self.add_action( action )

    # Handle very similar to the register functions, including priority
    patches = config.pop( "patches", {} )
    if len( patches ) > 0:
      priority = patches.pop( "priority", 0 )
      if priority not in self._patch_configs:
        self._patch_configs[priority] = {}
      self._patch_configs[priority][origin] = patches
    super().load_core_config( config, origin )

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
    if "virtual_relaunch" in action_id_list:
      action_id_list = action_id_list.copy()
      action_id_list.remove( "virtual_relaunch" )
    save_dict = self._load_save_dict()
    save_dict_update = {
                        "actions" :
                        {
                          action : self.actions[action].results for action in action_id_list
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
      if action == "virtual_relaunch":
        continue

      if action not in self.actions:
        tmp = self.save_file + ".backup"
        self.log( f"Loaded action info '{action}' missing from loaded workflow, state will be lost", level=30 )
        self.log( f"Making a copy of previous save file at '{tmp}'", level=30 )
        shutil.copy2( self.save_file, tmp )
        continue

      self.actions[action].results = action_dict

      if (
          # We never finished so reset
              ( self.actions[action].state == sane.action.ActionState.RUNNING )
          # We would like to re-attempt
          or ( clear_errors and self.actions[action].state == sane.action.ActionState.ERROR )
          or ( clear_failures and self.actions[action].status == sane.action.ActionStatus.FAILURE )
          ):
        self.actions[action].set_state_pending()

  def save_junit( self ):
    save_dict = self._load_save_dict()
    root = xmltree.Element( "testsuite" )
    root.set( "name", "workflow")
    tests = 0
    total_time = 0.0
    errors = 0
    failures = 0
    skipped = 0
    for action_name, results in save_dict["actions"].items():
      if action_name == "virtual_relaunch":
        continue

      node = xmltree.SubElement( root, "testcase" )
      tests += 1
      node.set( "name", action_name )
      node.set( "classname", results["origins"][0] )
      node.set( "file", results["origins"][1] )

      state = sane.action.ActionState( results["state"] )
      # Not running and not inactive, done in some capacity
      if not ( sane.action.ActionState.valid_run_state( state ) or state == sane.action.ActionState.INACTIVE ):
        node.set( "time", results["time"] )
        total_time += float( results["time"] )

      if state == sane.action.ActionState.ERROR:
        err = xmltree.SubElement( node, "error" )
        errors += 1
      elif state == sane.action.ActionState.SKIPPED:
        skip = xmltree.SubElement( node, "skipped" )
        skipped += 1
      elif sane.action.ActionStatus( results["status"] ) == sane.action.ActionStatus.FAILURE:
        fail = xmltree.SubElement( node, "failure" )
        failures += 1

      if len( results["origins"] ) > 2:
        props = xmltree.SubElement( node, "properties" )
        for i in range( 2, len( results["origins"] ) ):
          xmltree.SubElement( props, "property", { f"config{i-2}" : results["origins"][i] } )
    root.set( "time", f"{total_time:.6f}" )
    root.set( "tests", str(tests) )
    root.set( "failures", str(failures) )
    root.set( "errors", str(errors) )
    root.set( "skipped", str(skipped) )
    results_str = xml.dom.minidom.parseString( xmltree.tostring( root ) ).toprettyxml( indent="  " )
    with open( self.results_file, "w" ) as f:
      f.write( results_str )
