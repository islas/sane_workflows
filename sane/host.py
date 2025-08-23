import socket
from abc import ABCMeta, abstractmethod
import re
import math
import collections

import sane.config as config
import sane.environment
import sane.json_config as jconfig
import sane.logger as logger
import sane.resources as res
import sane.save_state as state
import sane.utdict as utdict
import sane.action


class Host( config.Config, state.SaveState, res.ResourceProvider ):
  CONFIG_TYPE = "Host"

  def __init__( self, name, aliases=[] ):
    super().__init__( name=name, aliases=aliases, logname=name, filename=f"host_{name}", base=Host )

    self.environments  = utdict.UniqueTypedDict( sane.environment.Environment )
    self.lmod_path     = None
    self._resources    = {}
    # self._kw_resources = { "cpus" : 0, "gpus" : 0, "mem" : 0 }
    # for kw_res in self._kw_resources:
    #   self.add_resources( self._kw_resources )

    self._default_env  = None

  def match( self, requested_host ):
    return self.partial_match( requested_host )

  def valid_host( self, override_host=None ):
    requested_host = socket.getfqdn() if override_host is None else override_host
    return self.match( requested_host )

  def has_environment( self, requested_env ):
    if requested_env is None:
      # Note that this is the property
      return self.default_env

    env = None
    for env_name, environment in self.environments.items():
      found = environment.match( requested_env )
      if found:
        env = environment
        break

    return env

  @property
  def default_env( self ):
    if self._default_env is None:
      return None
    else:
      return self.has_environment( self._default_env )

  @default_env.setter
  def default_env( self, env ):
    self._default_env = env

  def add_environment( self, env ):
    if env.lmod_path is None and self.lmod_path is not None:
      env.lmod_path = self.lmod_path
    self.environments[env.name] = env

  def load_core_config( self, config ):
    aliases = list( set( config.pop( "aliases", [] ) ) )
    if aliases != []:
      self._aliases = aliases

    default_env = config.pop( "default_env", None )
    if default_env is not None:
      self.default_env = default_env

    lmod_path = config.pop( "lmod_path", None )
    if lmod_path is not None:
      self.lmod_path = lmod_path

    env_configs      = config.pop( "environments", {} )
    for id, env_config in env_configs.items():
      env_typename = env_config.pop( "type", sane.environment.Environment.CONFIG_TYPE )
      env_type = sane.environment.Environment
      if env_typename != sane.environment.Environment.CONFIG_TYPE:
        env_type = self.search_type( env_typename )

      env = env_type( id )
      env.load_config( env_config )

      self.add_environment( env )

    super().load_core_config( config )

  def pre_launch( self, action ):
    pass

  def post_launch( self, action, retval, content ):
    pass

  def launch_wrapper( self, action, dependencies ):
    pass


class HPCHost( Host ):
  def __init__( self, name, aliases=[] ):
    super().__init__( name=name, aliases=aliases )
    # Maybe find a better way to do this
    self._base = HPCHost

    # Defaults
    self.queue   = None
    self.account = None
    self.default_local = False

    self._job_ids = {}

    # These must be filled out by derived classes
    self._status_cmd = None
    self._submit_cmd = None
    self._resources_delim = None
    self._amount_delim = None
    self._submit_format =  {
                            "arguments"  : "",
                            "name"       : "",
                            "dependency" : "",
                            "queue"      : "",
                            "account"    : "",
                            "output"     : "",
                            "time"       : "",
                            "wait"       : ""
                            }

  def load_core_config( self, config ):
    queue = config.pop( "queue", None )
    if queue is not None:
      self.queue = queue

    account = config.pop( "account", None )
    if account is not None:
      self.account = account

    super().load_core_config( config )

  def _format_arguments( self, arguments ):
    resources = []
    for option, resource_list in arguments:
      output = self._resources_delim.join(
                                            [
                                              resource + ( "" if amount == "" else f"{self._amount_delim}{amount}" )
                                              for resource, amount in resource_list
                                            ]
                                          )
      resources.extend( [ option, output ] )
    return " ".join( resources )

  def _format_dependencies( self, dependencies ):
    return ",".join(
                      [
                        dep_type.value + ":" + ":".join( [ str( job_id ) for job_id in dep_jobs ] )
                        for dep_type, dep_jobs in dependencies.items() if len( dep_jobs ) > 0
                      ]
                    )

  def _format_submission( self, submit_values ):
    submission = []
    for key, value in submit_values.items():
      if key in self._submit_format and value is not None:
        submission.extend( self._submit_format[key].format( value ).split( " " ) )
    return submission

  def _launch_local( self, action ):
    return action.local or ( action.local is None and self.default_local )

  def post_launch( self, action, retval, content ):
    if not self._launch_local( action ):
      if retval != 0:
        msg = f"Submission of Action {action.id} failed. Will not have job id"
        self.log( msg, level=40 )
        raise Exception( msg )
      self._job_ids[action.id] = self.extract_job_id( content )
    super().post_launch( action, retval, content )

  def job_complete( self, job_id ):
    proc = subprocess.Popen(
                            [ self._status_cmd, str( job_id ) ],
                            stdin =subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                            )
    output, err = proc.communicate()
    retval    = proc.returncode
    ouptut    = output.decode( "utf-8" )
    return self.check_job_status( retval, output )

  def launch_wrapper( self, action, dependencies ):
    """A launch wrapper must be defined for HPC submissions"""
    if self._launch_local( action ):
      return None

    dep_jobs = {}
    for id, dep_action in dependencies.items():
      if not self._launch_local( dep_action ):
        if action.dependencies[id] not in dep_jobs:
          dep_jobs[action.dependencies[id]] = []
        # Construct dependency type -> job id
        dep_jobs[action.dependencies[id]].append( self._job_ids[dep_action.id] )

    specific_resources = action.resources( host=self.name ) 
    queue = specific_resources.get( "queue", self.queue )
    account = specific_resources.get( "account", self.account )
    timelimit = specific_resources.get( "timelimit", None )

    if queue is None or account is None:
      missing = "queue" if queue is None else "account"
      msg = f"No {missing} provided for Host {host.name} or Action {action.id} in HPC submission"
      self.log( msg, level=40 )
      raise Exception( msg )

    submit_args = self.convert_to_host_resources( specific_resources )

    submit_values = self.get_submit_values(
                                            action,
                                            {
                                              "arguments"  : self._format_arguments( submit_args ),
                                              "dependency" : self._format_dependencies( dep_jobs ),
                                              "name"       : f"sane.workflow.{action.id}",
                                              "output"     : action.logfile,
                                              "queue"      : queue,
                                              "account"    : account,
                                              "time"       : timelimit,
                                            }
                                          )
    return self._format_submission( submit_values )

  @abstractmethod
  def check_job_status( self, retval, status ):
    """Tell us how to evaluate the job status command output

    The return value should be a bool noting whether a job has completed, 
    regardless of pass or fail.
    """
    pass

  @abstractmethod
  def extract_job_id( self, content ):
    """Tell us how to extract the job id from the return stdout of submission

    The return value should be the job id used in dependency and status checks
    """
    pass

  @abstractmethod
  def convert_to_host_arguments( self, resource_dict ):
    """Tell us how to interpret action resource request for this host

    The return value should be a list of tuples with flag/option and list of
    tuples of key and optional value as a str
    [ ( flag, [( res0, "amount" ), ( res1 )] ), (...) ]

    This should be able to be passed directly into format_resources()
    """
    pass

  def get_submit_values( self, action, initial_submit_values ):
    """Tell us the values to use when populating the submit_format template

    The return value should be a dict with keys being a subset of the internal
    submit_format template of this host. Not all keys must be present in the return
    value, however all keys in the return value dict should be `in` the internal
    submit_format template.
    """
    # Normally this should be enough
    return initial_submit_values


class PBSHost( HPCHost ):
  def __init__( self, name, aliases=[] ):
    super().__init__( name=name, aliases=aliases )
    # Maybe find a better way to do this
    self._base = PBSHost

    # Job ID finder
    self._job_id_regex  = re.compile( r"(\d{5,})" )

    # Cache previous submission arguments
    self._submit_arguments = {}

    self._status_cmd = "qstat"
    self._submit_cmd = "qsub"
    self._resources_delim = ":"
    self._amount_delim = "="
    self._submit_format["arguments"]  = "{0}",
    self._submit_format["name"]       = "-N {0}",
    self._submit_format["dependency"] = "-W depend={0}",
    self._submit_format["queue"]      = "-q {0}",
    self._submit_format["account"]    = "-A {0}",
    self._submit_format["output"]     = "-j oe -o {0}",
    self._submit_format["time"]       = "-l walltime={0}",
    self._submit_format["wait"]       = "-W block=true"

    self._mapper = res.ResourceMapper()

    self._mapper.add_mapping( "ncpus", ["cpus", "cpu"] )
    self._mapper.add_mapping( "ngpus", ["gpus", "gpu"] )

    hardware = {
                  "cpu_nodes" :
                  {
                    "nodes" : 2488, "exclusive" : True, "resources" : { "cpus" : 128, "memory" : "256gb" } },
                  "gpu_nodes" : { "nodes" : 82, "resources" : { "cpus" : 64, "memory" : "512gb", "gpus:a100" : 4 } },
                  "cpudev_nodes" : { "nodes" : 8, "exclusive" : False, "resources" : { "cpus" : 64, "memory" : "128gb" } }
                }
    self.hardware = {}
    self.log( "Loading homogeneous hardware definitions..." )
    self.log_push()
    for homogeneous_nodes, specs in hardware.items():
      self.log( f"Loading {homogeneous_nodes}" )
      self.log_push()
      nodes = int( specs.pop( "nodes" ) )
      self.hardware[homogeneous_nodes] = {
                                          "exclusive" : specs.pop( "exclusive", False ),
                                          "node" : res.ResourceProvider( logname=f"{self.name}::{homogeneous_nodes}" ),
                                          "total" : res.ResourceProvider( logname=f"{self.name}::{homogeneous_nodes}" )
                                        }
      self.hardware[homogeneous_nodes]["node"].add_resources( self.map_resource_dict( specs.get( "resources", {} ), log=True ) )
      self.hardware[homogeneous_nodes]["total"].add_resources( self.map_resource_dict( specs.get( "resources", {} ) ) )
      self.hardware[homogeneous_nodes]["total"].add_resources( self.map_resource_dict( { "nodes" : 1 } ) )
      # Modify them directly
      for res in self.hardware[homogeneous_nodes]["total"].resources:
        self.hardware[homogeneous_nodes]["total"]._resources[res]["numeric"] *= nodes
      self.log_pop()
    self.log_pop()



  def check_job_status( self, retval, status ):
    return ( retVal > 0 or output == "" )

  def extract_job_id( self, content ):
    found = self._job_id_regex.match( content )
    if found is None:
      self.log( "No job id found in output from job submission", level=40 )
      return -1
    else:
      return int( found.group( 1 ) )

  def convert_to_host_arguments( self ):
    pass

  def map_resource( self, resource ):
    """Map everything to internal name"""
    mapped_resource = self._mapper.name( resource )
    res_split = resource.split( ":" )
    if len( res_split ) == 2:
      mapped_resource = "{0}:{1}".format( self._mapper.name( res_split[0] ), res_split[1] )
    return mapped_resource

  def map_resource_dict( self, resource_dict, log=False ):
    """Map entire dict to internal names"""
    output_log = ( log and self._mapper.num_maps > 0 )
    if output_log:
      self.log( "Mapping resources with internal names..." )
      self.log_push()
    mapped_resource_dict = resource_dict.copy()
    for resource in resource_dict:
      mapped_resource = self.map_resource( resource )

      if mapped_resource != resource:
        if output_log:
          self.log( f"Mapping {resource} to internal name {mapped_resource}" )
        mapped_resource_dict[mapped_resource] = resource_dict[resource]
        del mapped_resource_dict[resource]
    if output_log:
      self.log_pop()
    return mapped_resource_dict

  def acquire_resource_from_nodes( self, resource_dict ):
    resource_dicts = [ resource_dict.copy() ]
    # Manual specification has been made, ignore everything else
    if "select" in resource_dict:
      selections = [
                    "nodes=" + options
                    for options in list(
                                        filter(
                                                None,
                                                resource_dict["select"].replace( "+", "select=" ).split( "select=" )
                                                )
                                        )
                  ]
      resource_dicts = []
      for select in selections:
        select_dict = {}
        for iter_match in re.finditer( r"(?P<res>\w+)=(?P<amount>.*?)(?=:|$)", select ):
          select_dict[iter_match.group( "res" )] = iter_match.group( "amount" )
        resource_dicts.append( select_dict )

    # Form the rest of the arguments
    host_arguments = []

    for res_dict in resource_dicts:
      # These are the resources we *can* provide
      available_resources = set()
      for homogeneous_nodes, node_resources in self.hardware.items():
        available_resources = available_resources | set( [ self._mapper.name( res ) for res in node_resources["node"].resources.keys() ] )

      specified_resource_dict = self.map_resource_dict( res_dict )
      # Map to specific name-mapped resources, converting generics to specifics
      # Use list to get the instantaneous resources
      for resource in list( specified_resource_dict.keys() ):
        for available_resource in available_resources:
          if resource != available_resource and resource == available_resource.split( ":" )[0]:
            specified_resource_dict[available_resource] = res_dict[resource]
            del specified_resource_dict[resource]
            # this generic resource has been specified, move to the next
            break

      # These are the resources that should be provided by the end of this
      required_resources = available_resources & set( specified_resource_dict.keys() )

      # Convert to base if possible
      for resource, amount in specified_resource_dict.items():
        res_size_dict = res.res_size_dict( specified_resource_dict[resource] )
        if res_size_dict is not None:
          specified_resource_dict[resource] = res.res_size_base( res_size_dict )

      submit_args = []
      resources_satisfied = {}
      node_pool_visited = {}
      print( f"required_resources : {required_resources}" )
      while len( resources_satisfied ) != len( required_resources ):
        nodeset_resources = set()
        nodeset_name  = None

        for homogeneous_nodes, node_resources in self.hardware.items():
          # Skip nodes that already provided resources and thus cannot provide more
          if homogeneous_nodes in node_pool_visited:
            continue
          # Naively find node type that best matches
          resources_provided = set( node_resources["node"].resources.keys() ) & required_resources
          print( f"{homogeneous_nodes} : {resources_provided}" )
          if len( resources_provided ) > len( nodeset_resources ):
            nodeset_resources = resources_provided
            nodeset_name = homogeneous_nodes

        print( nodeset_name )

        # Find max nodes needed for this homogeneous selection
        node_pool_visited[nodeset_name] = True
        nodes = specified_resource_dict.pop( "nodes", 0 )
        # available_node_resources = []
        if nodes == 0:
          for resource in nodeset_resources:
            available = self.hardware[nodeset_name]["total"].resources_available( { resource : specified_resource_dict[resource] } )
            if available:
              # Todo convert to numeric so as to compare against same units
              nodes_for_res = max( specified_resource_dict[resource] / self.hardware[nodeset_name]["node"].resources[resource]["numeric"], 1 )
              nodes = max( nodes, math.ceil(nodes_for_res) )
              # available_node_resources.append( resource )
        if not self.hardware[nodeset_name]["total"].resources_available( { "nodes" : nodes } ):
          return False, []

        # Find total amounts used
        select_amounts = {}
        amounts = {}
        # Use all applicable resources
        for resource in self.hardware[nodeset_name]["node"].resources.keys():
          amount = specified_resource_dict.get( resource, 0 )
          select_amount = math.ceil( amount / nodes )
          if self.hardware[nodeset_name]["exclusive"]:
            exclusive_amount = self.hardware[nodeset_name]["node"].resources[resource]["numeric"] * nodes
            if exclusive_amount != amount:
              original_mount = res.res_size_str( res.res_size_reduce( res.res_size_dict( amount ) ) ) 
              output_amount = res.res_size_str( res.res_size_reduce( res.res_size_dict( exclusive_amount ) ) )
              self.log( f"Current node is exclusive, changing resource '{resource}' amount from {original_mount} to {output_amount}" )
              amount = exclusive_amount

          # Check if available
          if self.hardware[nodeset_name]["total"].resources_available( { resource : amount } ):
            amounts[resource] = amount
            if select_amount > 0:
              select_amounts[resource] = select_amount
          # else
          # do not error out as this may be provided by another homogeneous select
        print( f"amounts : {amounts}" )
        print( f"select_amounts : {select_amounts}" )
        ################################################################################################################
        # Acquire resources and mark them as solved if needed
        # Finally construct the select
        if len( host_arguments ) == 0:
          # First select
          submit_args.append( ( "select", nodes ) )
        else:
          # Next homogeneous select
          submit_args.append( ( "+", nodes ) )

        amounts["nodes"] = nodes
        self.hardware[nodeset_name]["total"].acquire_resource( amounts )
        for resource, amount in select_amounts.items():
          print( resource )
          print( select_amounts[resource] )
          submit_args.append( ( resource, amount ) )
          specified_resource_dict[resource] -= amounts[resource]
          if specified_resource_dict[resource] <= 0:
            resources_satisfied[resource] = True
            del specified_resource_dict[resource]

      
      # Keep it specialized so others downstream know what we tried to solve
      if len( host_arguments ) == 0:
        host_arguments.append( ( "-l", submit_args ) )
      else:
        host_arguments[0][1].extend( submit_args )

      # derived_arguments = super().convert_to_host_resources( specified_resource_dict )
      # host_arguments.extend( derived_arguments )
    print( f"resource_dicts : {resource_dicts}" )
    return host_arguments

