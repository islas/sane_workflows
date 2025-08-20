import socket
from abc import ABCMeta, abstractmethod
import re

import sane.config as config
import sane.environment
import sane.json_config as jconfig
import sane.logger as logger
import sane.resource_helpers as reshelpers
import sane.save_state as state
import sane.utdict as utdict
import sane.action


class Host( config.Config, state.SaveState, jconfig.JSONConfig ):
  CONFIG_TYPE = "Host"

  def __init__( self, name, aliases=[] ):
    super().__init__( name=name, aliases=aliases, filename=f"host_{name}", base=Host )

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

    self.add_resources( config.pop( "resources", {} ) )

    env_configs      = config.pop( "environments", {} )
    for id, env_config in env_configs.items():
      env_typename = env_config.pop( "type", sane.environment.Environment.CONFIG_TYPE )
      env_type = sane.environment.Environment
      if env_typename != sane.environment.Environment.CONFIG_TYPE:
        env_type = self.search_type( env_typename )

      env = env_type( id )
      env.load_config( env_config )

      self.add_environment( env )

  def add_resources( self, resource_dict ):
    for resource, info in resource_dict.items():
      if resource in self._resources and self._resources[resource]["numeric"] > 0:
        self.log( f"Resource ''{resource}'' already set, ignoring new resource setting", level=30 )
      else:
        self._resources[resource] = reshelpers.res_size_expand( reshelpers.res_size_dict( str(info) ) )
        self._resources[resource]["in_use"] = 0.0

  def resources_available( self, resource_dict, requestor=None ):
    origin_msg = ""
    if requestor is not None:
      origin_msg = f" for {requestor}"

    self.log( f"Checking if resources available{origin_msg}..." )
    self.log_push()
    can_aquire = True
    for resource, info in resource_dict.items():
      res_size_dict = reshelpers.res_size_dict( info )
      if resource not in self._resources:
        msg  = f"Will never be able to acquire resource '{resource}' : {info}, "
        msg += "host does not possess this resource"
        self.log( msg, level=50 )
        self.log_pop()
        raise Exception( msg )

      req_amount = reshelpers.res_size_base( res_size_dict )
      if req_amount > self._resources[resource]["numeric"]:
        msg  = f"Will never be able to acquire resource '{resource}' : {info}, "
        msg += "requested amount is greater than available total " + reshelpers.res_size_str(self._resources[resource])
        self.log( msg, level=50 )
        self.log_pop()
        raise Exception( msg )

      acquirable = ( req_amount + self._resources[resource]["in_use"] ) <= self._resources[resource]["numeric"]
      if not acquirable:
        self.log( f"Resource '{resource}' : {amount}{base_unit} not acquirable right now..." )
      can_aquire = can_aquire and acquirable
    self.log( f"All resources{origin_msg} available" )
    self.log_pop()
    return can_aquire

  def acquire_resource( self, resource_dict, requestor=None ):
    origin_msg = ""
    if requestor is not None:
      origin_msg = f" for {requestor}"

    self.log( f"Acquiring resources{origin_msg}..." )
    self.log_push()
    if self.resources_available( resource_dict, requestor ):
      for resource, info in resource_dict.items():
        self.log( f"Acquiring resource '{resource}' : {info}")
        self._resources[resource]["in_use"] += reshelpers.res_size_base( reshelpers.res_size_dict( info ) )
    else:
      self.log( f"Could not acquire resources{origin_msg}", level=30 )
      self.log_pop()
      return False

    self.log_pop()
    return True

  def release_resources( self, resource_dict, requestor=None ):
    origin_msg = ""
    if requestor is not None:
      origin_msg = f" from {requestor}"

    self.log( f"Releasing resources{origin_msg}..." )
    self.log_push()
    for resource, info in resource_dict.items():
      if resource not in self._resources:
        self.log( f"Cannot return resource '{resource}', instance does not possess this resource", level=30 )
      amount = reshelpers.res_size_base( reshelpers.res_size_dict( info ) )
      in_use = self._resources[resource]["in_use"]
      if ( in_use - amount ) < 0:
        tmp = self._resources[resource].copy()
        tmp["numeric"] = in_use
        msg  = f"Cannot return resource '{resource}' : {info}, "
        msg += "amount is greater than current in use " + reshelpers.res_size_str( tmp )
        self.log( msg, level=30 )
      else:
        self.log( f"Releasing resource '{resource}' : {info}" )
        self._resources[resource]["in_use"] -= amount
    self.log_pop()

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

    self.default_local = False

    self._job_ids = {}

    # These must be filled out by derived classes
    self._status_cmd = None
    self._submit_cmd = None
    self._resources_delim = None
    self._amount_delim = None
    self._submit_format = {}

  def _format_resources( resources ):
    resources = []
    for option, resource_dict in resources:
      output = self._resources_delim.join(
                                            [
                                              resource + ( "" if amount == "" else f"{self._amount_delim}{amount}" )
                                              for resource, amount in resource_dict.items()
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
      if key in self._submit_format:
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

    specific_resources = self.convert_to_host_resources( action.resources )
    dep_jobs = {}
    for id, dep_action in dependencies.items():
      if not self._launch_local( dep_action ):
        if action.dependencies[id] not in dep_jobs:
          dep_jobs[action.dependencies[id]] = []
        # Construct dependency type -> job id
        dep_jobs[action.dependencies[id]].append( self._job_ids[dep_action.id] )

    submit_values = self.get_submit_values(
                                            action,
                                            self._format_resources( specific_resources ),
                                            self._format_dependencies( dep_jobs )
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
  def convert_to_host_resources( self, resource_dict ):
    """Tell us how to interpret action resource request for this host

    The return value should be a list of tuples with flag/option and dict
    of resource and any amount as a str: [ ( flag : { res0 : "amount", res1 : "" } ), (...) ]

    This should be able to be passed directly into format_resources()
    """
    pass

  @abstractmethod
  def get_submit_values( self, action, resource_str, dependency_str ):
    """Tell us the values to use when populating the submit_format template

    The return value should be a dict with keys being a subset of the internal
    submit_format template of this host. Not all keys must be present in the return
    value, however all keys in the return value dict should be `in` the internal
    submit_format template.
    """
    pass


class PBSHost( HPCHost ):
  CONFIG_TYPE = "PBSHost"

  def __init__( self, name, aliases=[] ):
    super().__init__( name=name, aliases=aliases )
    # Maybe find a better way to do this
    self._base = PBSHost

    # Job ID finder
    self._job_id_regex  = re.compile( r"(\d{5,})" )

    self._status_cmd = "qstat"
    self._submit_cmd = "qsub"
    self._resources_delim = ":"
    self._amount_delim = "="
    self._submit_format = {
                            "resources"  : "{0}",
                            "name"       : "-N {0}",
                            "dependency" : "-W depend={0}",
                            "queue"      : "-q {0}",
                            "account"    : "-A {0}",
                            "output"     : "-j oe -o {0}",
                            "time"       : "-l walltime={0}",
                            "wait"       : "-W block=true"
                            }

    # Defaults
    self.queue   = None
    self.account = None

  def load_core_config( self, config ):
    queue = config.pop( "queue", None )
    if queue is not None:
      self.queue = queue

    account = config.pop( "account", None )
    if account is not None:
      self.account = account

  def check_job_status( self, retval, status ):
    return ( retVal > 0 or output == "" )

  def extract_job_id( self, content ):
    found = self._job_id_regex.match( content )
    if found is None:
      self.log( "No job id found in output from job submission", level=40 )
      return -1
    else:
      return int( found.group( 1 ) )

  # You must still provide this host
  # @abstractmethod
  # def convert_to_host_resources( self, resource_dict ):

  @abstractmethod
  def get_submit_values( self, action, resource_str, dependency_str ):
    queue = self._queue
    account = self._account
    if f"{self.name}:queue" in action.config:
      queue = action.config[f"{self.name}:queue"]

    if f"{self.name}:account" in action.config:
      account = action.config[f"{self.name}:account"]

    if queue is None or account is None:
      missing = "queue" if queue is None else "account"
      msg = f"No {missing} provided for Host {host.name} or Action {action.id} in HPC submission"
      self.log( msg, level=40 )
      raise Exception( msg )

    submit_values = {
                      "name"       : f"sane.{action.id}-{self._job_ids[action.id]}",
                      "queue"      : queue,
                      "account"    : account,
                      "output"     : action.logfile,
                    }

    if action.timelimit is not None:
      submit_values["time"] = action.timelimit
    if resource_str:
      submit_values["resources"] = resource_str
    if dependency_str:
      submit_values["dependency"] = dependency_str
