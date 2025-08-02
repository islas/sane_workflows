import unittest
import os

import sane


class EnvironmentTests( unittest.TestCase ):
  def setUp( self ):
    self.environment = sane.Environment( "test" )

  def test_environment_standalone( self ):
    """Ensure that an environment can be created standalone"""
    pass

  def test_environment_setup_env_var_noop_internal( self ):
    """When utilizing setup_env_vars() make sure the current environment is unchanged"""
    env = dict( os.environ.copy() )
    self.environment.setup_env_vars( "prepend", "PATH", "/usr/notbin/" )
    self.environment.setup_env_vars( "append",  "PATH", "/usr/yesbin/" )
    self.environment.setup_env_vars( "set",     "HOME", "/definitely/my/home/" )
    self.environment.setup_env_vars( "unset",   "USERNAME" )
    post_env = dict( os.environ.copy() )
    self.assertEqual( env, post_env )

  def test_environment_env_var_func_mod_internal( self ):
    """When utilizing env_var_*() functions the current environment is modified"""
    env = dict( os.environ.copy() )
    self.environment.env_var_set(     "OLDUSEFUL_VARIABLE", "/definitely/my/home/" )
    self.environment.env_var_prepend( "OLDUSEFUL_VARIABLE", "/usr/notbin/" )
    self.environment.env_var_append(  "OLDUSEFUL_VARIABLE", "/usr/yesbin/" )
    self.environment.env_var_set(     "NEWUSEFUL_VARIABLE", "/super_useful/" )
    self.environment.env_var_unset(   "NEWUSEFUL_VARIABLE" )
    post_env = dict( os.environ.copy() )
    self.assertNotEqual( env, post_env )

    self.assertNotIn( "OLDUSEFUL_VARIABLE", env )
    self.assertIn( "OLDUSEFUL_VARIABLE", post_env )
    self.assertNotIn( "NEWUSEFUL_VARIABLE", post_env )
    self.assertEqual( post_env["OLDUSEFUL_VARIABLE"], "/usr/notbin/:/definitely/my/home/:/usr/yesbin/" )
