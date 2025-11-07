from abc import abstractmethod
import re
import math
import time
import subprocess

import sane.action
import sane.resources
import sane.host


class HPCHost( sane.resources.NonLocalProvider, sane.host.Host ):
  HPC_DELAY_PERIOD_SECONDS = 5

  def __init__( self, name, aliases=[] ):
    super().__init__( name=name, aliases=aliases )
    # Maybe find a better way to do this
    self._base = HPCHost

    # Defaults
    self.queue   = None
    self.account = None

    self.job_suffix = ""

    self._job_ids = {}

    # These must be filled out by derived classes
    self._state_cmd = None
    self._status_cmd = None
    self._submit_cmd = None
    self._resources_delim = None
    self._amount_delim = None
    self._submit_format = {
                            "arguments"  : "",
                            "name"       : "",
                            "dependency" : "",
                            "queue"      : "",
                            "account"    : "",
                            "output"     : "",
                            "time"       : "",
                            "wait"       : ""
                          }
    self._cmd_delim = None

  def load_core_config( self, config, origin ):
    queue = config.pop( "queue", None )
    if queue is not None:
      self.queue = queue

    account = config.pop( "account", None )
    if account is not None:
      self.account = account

    self.job_suffix = config.pop( "job_suffix", "" )

    super().load_core_config( config, origin )

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
    if self._cmd_delim is not None:
      submission.append( self._cmd_delim )
    return submission

  @property
  def watchdog_func( self ):
    return self.capture_job_complete

  def capture_job_complete( self, actions, only_watchdog=True ):
    completed = {}
    while not self.kill_watchdog and ( only_watchdog or len( completed ) != len( self._job_ids ) ):
      time.sleep( HPCHost.HPC_DELAY_PERIOD_SECONDS )
      for action_name, job_id in self._job_ids.items():
        if action_name not in completed and ( self.dry_run or self.job_complete( job_id ) ):
          completed[action_name] = job_id
          status = self.dry_run or self.job_status( job_id )
          disclaimer = ""
          if self.dry_run:
            disclaimer = " (dry-run)"
          self.log( f"Action '{action_name}' with job ID {job_id} complete. Success : {status}{disclaimer}" )
          if status:
            actions[action_name].set_status_success()
          else:
            actions[action_name].set_status_failure()
          # Wake the orch
          self.__orch_wake__()

  def post_launch( self, action, retval, content ):
    if not self.launch_local( action ):
      if retval != 0:
        msg = f"Submission of Action '{action.id}' failed. Will not have job id"
        self.log( msg, level=40 )
        raise Exception( msg )
      self._job_ids[action.id] = self.extract_job_id( content )
    super().post_launch( action, retval, content )

  def post_run_actions( self, actions ):
    if not self.dry_run and len( self._job_ids ) > 0:
      self.log( "Waiting for HPC jobs to complete" )
      self.log_push()
      self.log( "*ATTENTION* : This is a blocking/sync phase to wait for all jobs to complete - BE PATIENT" )
      self.kill_watchdog = False
      self.capture_job_complete( actions, only_watchdog=False )
      self.log_pop()
      self.log( "All HPC jobs complete" )
    elif self.dry_run:
      self.log( "Dry run, no HPC jobs to wait for, marking all as success" )
      for action_name, job_id in self._job_ids.items():
        actions[action_name].set_status_success()
    else:
      self.log( "No HPC jobs to wait for" )
    super().post_run_actions( actions )

  def job_complete( self, job_id ):
    proc = subprocess.Popen(
                            ( self._state_cmd + f" {job_id}" ).split( " " ),
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                            )
    output, err = proc.communicate()
    retval = proc.returncode
    output = output.decode( "utf-8" )
    return self.check_job_complete( job_id, retval, output )

  def job_status( self, job_id ):
    proc = subprocess.Popen(
                            ( self._status_cmd + f" {job_id}" ).split( " " ),
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                            )
    output, err = proc.communicate()
    retval = proc.returncode
    output = output.decode( "utf-8" )
    return self.check_job_status( job_id, retval, output )

  def launch_wrapper( self, action, dependencies ):
    """A launch wrapper must be defined for HPC submissions"""
    if self.launch_local( action ):
      return None

    dep_jobs = {}
    for id, dep_action in dependencies.items():
      if not self.launch_local( dep_action ):
        if dep_action.status == sane.action.ActionStatus.SUBMITTED:
          if action.dependencies[id]["dep_type"] not in dep_jobs:
            # quickly add the key for this type of dependency
            dep_jobs[action.dependencies[id]["dep_type"]] = []
          # Construct dependency type -> job id
          if dep_action.id not in self._job_ids:
            raise KeyError( f"Missing job id for '{dep_action.id}'" )
          else:
            dep_jobs[action.dependencies[id]["dep_type"]].append( self._job_ids[dep_action.id] )
        # else:
          # We should not need to do this as the orch would be the one to check
          # that our dependencies were met before asking this action to launch
          # Check that the previously run action could satisfy this

    specific_resources = action.resources( override=self.name )
    queue = specific_resources.get( "queue", self.queue )
    account = specific_resources.get( "account", self.account )
    timelimit = specific_resources.get( "timelimit", None )

    if queue is None or account is None:
      missing = "queue" if queue is None else "account"
      msg = f"No {missing} provided for Host {self.name} or Action {action.id} in HPC submission resources"
      self.log( msg, level=40 )
      raise KeyError( msg )

    submit_args = self.submit_args( specific_resources, action.logname )
    default_submit = {
                              "name"       : f"sane.workflow.{action.id}{self.job_suffix}",
                              "output"     : action.logfile,
                              "queue"      : queue,
                              "account"    : account,
                              "time"       : timelimit,
                            }
    if len( submit_args ) > 0:
      default_submit["arguments"] = self._format_arguments( submit_args )
    if len( dep_jobs ) > 0:
      default_submit["dependency"] = self._format_dependencies( dep_jobs )

    submit_values = self.get_submit_values( action, default_submit )
    return self._submit_cmd, self._format_submission( submit_values )

  def get_submit_values( self, action, initial_submit_values ):
    """Tell us the values to use when populating the submit_format template

    The return value should be a dict with keys being a subset of the internal
    submit_format template of this host. Not all keys must be present in the return
    value, however all keys in the return value dict should be `in` the internal
    submit_format template.
    """
    # Normally this should be enough
    return initial_submit_values

  @abstractmethod
  def check_job_complete( self, job_id, retval, status ):
    """Tell us how to evaluate the job complete command output

    The return value should be a bool noting whether a job has completed,
    regardless of pass or fail.
    """
    pass

  @abstractmethod
  def check_job_status( self, job_id, retval, status ):
    """Tell us how to evaluate the job status command output

    The return value should be a bool noting whether a job exit status
    was successful, returning False if not
    """
    pass

  @abstractmethod
  def extract_job_id( self, content ):
    """Tell us how to extract the job id from the return stdout of submission

    The return value should be the job id used in dependency and status checks
    """
    pass

  @abstractmethod
  def submit_args( self, resource_dict, requestor_name ):
    """Convert the resource dict from the requestor into hpc submission arguments

    The return should be of the format acceptable by _format_arguments()
    """
    pass


class PBSHost( HPCHost ):
  CONFIG_TYPE = "PBSHost"

  def __init__( self, name, aliases=[] ):
    super().__init__( name=name, aliases=aliases )
    # Maybe find a better way to do this
    self._base = PBSHost

    # Job ID finder
    self._job_id_regex  = r"(\d{5,})"

    # Cache previous submissions
    self._requisitions = {}

    # Keep job info around after query
    self._job_info = {}

    self._state_cmd = "qstat -f -x"
    self._status_cmd = self._state_cmd  # same thing
    self._submit_cmd = "qsub"
    self._resources_delim = ":"
    self._amount_delim = "="
    self._submit_format["arguments"]  = "{0}"
    self._submit_format["name"]       = "-N {0}"
    self._submit_format["dependency"] = "-W depend={0}"
    self._submit_format["queue"]      = "-q {0}"
    self._submit_format["account"]    = "-A {0}"
    self._submit_format["output"]     = "-j oe -o {0}"
    self._submit_format["time"]       = "-l walltime={0}"
    self._submit_format["wait"]       = "-W block=true"
    self._cmd_delim = "--"

  def log_push( self, levels=1 ):
    super().log_push( levels )
    for nodeset_name, nodeset in self._resources.items():
      nodeset["total"].log_push( levels )
      nodeset["node"].log_push( levels )

  def log_pop( self, levels=1 ):
    super().log_pop( levels )
    for nodeset_name, nodeset in self._resources.items():
      nodeset["total"].log_pop( levels )
      nodeset["node"].log_pop( levels )

  def load_core_config( self, config, origin ):
    # Note: This is very delicate and maybe should be restructured
    # Pull out resources first to override
    resources = config.pop( "resources", {} )

    # Now read rest of config *first* in case we have mappings
    super().load_core_config( config, origin )

    # Finally process resources
    for node_type, hardware_info in resources.items():
      if not isinstance( hardware_info, dict ) or "nodes" not in hardware_info or "resources" not in hardware_info:
        msg  = "HPC node resources must be a dict"
        msg += " { 'nodes' : int, 'exclusive' : bool|false, 'resources' : {<resource dict>} }"
        self.log( msg, level=50 )
        raise TypeError( msg )
      else:
        nodes = int( hardware_info["nodes"] )
        exclusive = hardware_info.get( "exclusive", False )
        node_resource_dict = hardware_info["resources"]
        self.add_resources( node_type, node_resource_dict, nodes, exclusive )

  def add_resources( self, node_type, node_resource_dict, nodes, exclusive=False ):
    if node_type in self._resources:
      self.log( f"Node type '{node_type}' already exists" )
    else:
      self.log( f"Adding homogeneous node resources for '{node_type}'" )
      self._resources[node_type] = {
                                      "exclusive" : exclusive,
                                      "node" : sane.resources.ResourceProvider( mapper=self._mapper, logname=f"{self.name}::{node_type}" ),
                                      "total" : sane.resources.ResourceProvider( mapper=self._mapper, logname=f"{self.name}::{node_type}" )
                                    }
      self._resources[node_type]["node"].add_resources( node_resource_dict )
      self._resources[node_type]["total"].add_resources(
                                                        {
                                                          res_name : (res.acquirable * nodes).amount
                                                          for res_name, res in self._resources[node_type]["node"].resources.items()
                                                        }
                                                      )
      self._resources[node_type]["total"].add_resources( { "nodes" : nodes } )

  def check_job_complete( self, job_id, retval, status ):
    if retval != 0:
      return False

    info = {}
    last_key = None
    for line in status.splitlines():
      kv = re.match( r"[ ]*(?P<key>(?:\w|[.-])+)[ ]*=[ ]*(?P<val>.*?)$", line )
      if kv is not None:
        info[kv.group("key").lower()] = kv.group("val")
        last_key = kv.group("key").lower()
      elif last_key is not None:
        info[last_key] += line.lstrip()

    self._job_info[job_id] = info
    if "job_state" in self._job_info[job_id] and self._job_info[job_id]["job_state"] == "F":
      return True
    else:
      return False

  def check_job_status( self, job_id, retval, status ):
    # Mostly call this again to reprocess output to latest
    complete = self.check_job_complete( job_id, retval, status )
    if not complete:
      # Something happened such that we thought we were complete but now aren't
      # Just mark as failure
      return False

    if "exit_status" in self._job_info[job_id]:
      return int(self._job_info[job_id]["exit_status"]) == 0
    else:
      return False

  def extract_job_id( self, content ):
    found = re.match( self._job_id_regex, content )
    if found is None:
      self.log( "No job id found in output from job submission", level=40 )
      raise RuntimeError( "No job id found" )
    else:
      return int( found.group( 1 ) )

  def pbs_resource_requisition( self, resource_dict, requestor ):
    self.log( f"Original resource request from '{requestor.logname}' : {resource_dict}", level=15 )

    resource_dicts = [ self.map_resource_dict( resource_dict ) ]
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

    requisition = {}
    resolved = True
    for res_dict in resource_dicts:
      # These are the resources we *can* provide
      available_resources = set()
      for homogeneous_nodes, node_resources in self._resources.items():
        available_resources = available_resources | set( node_resources["node"].resources.keys() )

      specified_resource_dict = res_dict.copy()
      # Map to specific name-mapped resources, converting generics to specifics
      # Use list to get the instantaneous resources
      for resource in list( specified_resource_dict.keys() ):
        for available_resource in available_resources:
          if resource != available_resource and resource == available_resource.split( ":" )[0]:
            specified_resource_dict[available_resource] = res_dict[resource]
            del specified_resource_dict[resource]
            # this generic resource has been specified, move to the next
            break

      # Only operate on numeric resources
      numeric_resources = []
      for resource in specified_resource_dict.keys():
        if sane.resources.Resource.is_resource( specified_resource_dict[resource] ):
          specified_resource_dict[resource] = sane.resources.Resource( resource, specified_resource_dict[resource] ).total
          numeric_resources.append( resource )

      self.log( f"Finding resources for '{requestor.logname}' : {specified_resource_dict}", level=15 )

      # These are the resources that should be provided by the end of this
      required_resources = available_resources & set( numeric_resources )

      resources_satisfied = {}
      node_pool_visited = {}
      while len( resources_satisfied ) != len( required_resources ):
        nodeset_resources = set()
        nodeset_name  = None

        for homogeneous_nodes, node_resources in self._resources.items():
          # Skip nodes that already provided resources and thus cannot provide more
          if homogeneous_nodes in node_pool_visited:
            continue
          # Naively find node type that best matches
          resources_provided = set( node_resources["node"].resources.keys() ) & required_resources
          if len( resources_provided ) > len( nodeset_resources ):
            nodeset_resources = resources_provided
            nodeset_name = homogeneous_nodes

        if nodeset_name is None:
          # Unsatisfied
          break

        self.log( f"Checking resources from '{nodeset_name}'", level=15 )
        node  = self._resources[nodeset_name]["node"]
        total = self._resources[nodeset_name]["total"]
        total.log_push( 2 )

        # Find max nodes needed for this homogeneous selection
        node_pool_visited[nodeset_name] = True
        nodes = specified_resource_dict.pop( "nodes", 0 )
        if nodes == 0:
          for resource in nodeset_resources:
            available = total.resources_available(
                                                  { resource : specified_resource_dict[resource] },
                                                  requestor=requestor,
                                                  log=False
                                                  )
            if available:
              nodes_for_res = max( specified_resource_dict[resource] / node.resources[resource].total, 1 )
              nodes = max( nodes, math.ceil(nodes_for_res) )

        if not total.resources_available( { "nodes" : nodes }, requestor=requestor, log=False ):
          total.log( "Not enough nodes", level=15 )
          total.log_pop( 2 )
          continue

        # Find total amounts and select amounts to be used in submission which differ if using multiple nodes
        select_amounts = {}
        amounts = {}
        # Use all applicable resources
        for resource in node.resources.keys():
          amount = specified_resource_dict.get( resource, 0 )
          unit = node.resources[resource].unit
          if unit:
            # Convert to usable unit amount then back to base in case it went up
            amount = sane.resources.Resource(
                                              resource,
                                              sane.resources.Resource(
                                                                      resource,
                                                                      amount,
                                                                      unit=unit
                                                                      ).total_str
                                              ).total

          select_amount = math.ceil( amount / nodes )
          if self._resources[nodeset_name]["exclusive"]:
            exclusive_amount = node.resources[resource].acquirable * nodes
            if exclusive_amount.total != amount:
              original_mount = sane.resources.Resource( resource, amount, unit=exclusive_amount.unit )
              msg  = f"Current node is exclusive, changing resource '{resource}' acquisition amount "
              msg += f"from {original_mount.total_str} to {exclusive_amount.total_str}"
              total.log( msg, level=15 )
              amount = exclusive_amount.total

          # Check if available
          if total.resources_available( { resource : amount }, requestor=requestor, log=False ):
            amounts[resource] = amount
            if select_amount > 0:
              if unit:
                select_amount = sane.resources.Resource( resource, select_amount, unit=unit ).total_str

              select_amounts[resource] = select_amount
          # else
          # do not error out as this may be provided by another homogeneous select

        amounts["nodes"] = nodes
        requisition[nodeset_name] = { "amounts" : amounts, "select_amounts" : select_amounts, "nodes" : nodes }

        # This is a duplication of the logic above, but just a whole check
        available = total.resources_available( amounts, requestor=requestor )
        # mark not available this time as amounts has already been filtered
        resolved = resolved and available
        if not available:
          total.log( f"Current node set '{nodeset_name}' not able to fully provide resources", level=15 )

        # Note how much we have resolved from the specified resource dict so that
        for resource, amount in amounts.items():
          if resource in specified_resource_dict:
            specified_resource_dict[resource] -= amounts[resource]
            if specified_resource_dict[resource] <= 0:
              resources_satisfied[resource] = True
              del specified_resource_dict[resource]

        total.log_pop( 2 )

      current_resolved = ( len( specified_resource_dict ) == 0 )
      resolved = resolved and current_resolved
      if not current_resolved:
        self.log( f"Did not fully resolve resource request : {res_dict}", level=15 )
        self.log( f"  Remaining : {specified_resource_dict}", level=15 )
    if resolved:
      self.log( f"HPC resources available for '{requestor.logname}'", level=15 )
    return resolved, requisition

  def submit_args( self, resource_dict : dict, requestor_name : str ):
    return self.requisition_to_submit_args( self._requisitions[requestor_name] )

  def requisition_to_submit_args( self, requisition ):
    host_arguments = []
    for nodeset, req in requisition.items():
      submit_args = []
      if len( host_arguments ) == 0:
        # First select
        submit_args.append( ( "select", req["nodes"] ) )
      else:
        # Next homogeneous select
        submit_args.append( ( "+", req["nodes"] ) )

      for resource, amount in req["select_amounts"].items():
        submit_args.append( ( resource, amount ) )

      # Keep it specialized so others downstream know what we tried to solve
      if len( host_arguments ) == 0:
        host_arguments.append( ( "-l", submit_args ) )
      else:
        host_arguments[0][1].extend( submit_args )

    return host_arguments

  def remove_hpc_kw( self, resource_dict ):
    res_dict = resource_dict.copy()
    res_dict.pop( "account", None )
    res_dict.pop( "queue", None )
    res_dict.pop( "timelimit", None )
    return res_dict

  def nonlocal_resources_available( self, resource_dict : dict, requestor : sane.resources.ResourceRequestor, log=True ):
    self.log( f"Checking resources for '{requestor.logname}'", level=15 )
    self.log_push()
    available, *_ = self.pbs_resource_requisition( self.remove_hpc_kw( resource_dict ), requestor )
    self.log_pop()
    return available

  def nonlocal_acquire_resources( self, resource_dict : dict, requestor : sane.resources.ResourceRequestor ):
    self.log( f"Acquiring HPC resources for '{requestor.logname}'...", level=15 )
    self.log_push()
    available, requisition = self.pbs_resource_requisition( self.remove_hpc_kw( resource_dict ), requestor )
    if not available:
      self.log( f"Could not acquire resources for {requestor.logname}", level=15 )
      self.log_pop()
      return available

    for nodeset, req in requisition.items():
      self._resources[nodeset]["total"].log_push()
      self._resources[nodeset]["total"].acquire_resources( req["amounts"], requestor )
      self._resources[nodeset]["total"].log_pop()

    self._requisitions[requestor.logname] = requisition
    self.log_pop()
    return available

  def nonlocal_release_resources( self, resource_dict : dict, requestor : sane.resources.ResourceRequestor ):
    requisition = self._requisitions[requestor.logname]
    for nodeset, req in requisition.items():
      self._resources[nodeset]["total"].release_resources( req["amounts"], requestor )
    del self._requisitions[requestor.logname]
