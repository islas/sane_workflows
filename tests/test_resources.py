import unittest
import copy

import sane.resources as res


class ResourceTests( unittest.TestCase ):
  def setUp( self ):
    pass

  def tearDown( self ):
    pass

  def test_resource( self ):
    """Test standalone creation of an individual numeric resource"""
    res.Resource( "foo" )
    res.Resource( "foo", 0 )
    res.Resource( "foo", "0b" )
    res.Resource( "foo", "0gb" )
    res.Resource( "foo", "12gb" )

  def test_resource_operations( self ):
    """Test ability of resource to handle supported operations"""
    rhs_num = 2
    rhs_res = res.Resource( "foo", rhs_num )

    lhs = res.Resource( "foo", 4 )
    result = lhs + rhs_res
    self.assertEqual( lhs.total + rhs_num, result.total )

    result = lhs + rhs_num
    self.assertEqual( lhs.total + rhs_num, result.total )

    result = lhs - rhs_res
    self.assertEqual( lhs.total - rhs_num, result.total )

    result = lhs - rhs_num
    self.assertEqual( lhs.total - rhs_num, result.total )

    # result = lhs * rhs_res NOT VALID
    # self.assertEqual( lhs.total - rhs_num, result.total )

    result = lhs * rhs_num
    self.assertEqual( lhs.total * rhs_num, result.total )

    result = lhs / rhs_res
    self.assertEqual( lhs.total / rhs_num, result )
    self.assertIsInstance( result, int )

    result = lhs / rhs_num
    self.assertEqual( lhs.total / rhs_num, result.total )
    self.assertIsInstance( result, res.Resource )

    # Now try with units and scale
    rhs_num = 1024
    rhs_res = res.Resource( "foo", f"1kb" )

    lhs = res.Resource( "foo", "4kb" )
    result = lhs + rhs_res
    self.assertEqual( lhs.total + rhs_num, result.total )

    result = lhs + rhs_num
    self.assertEqual( lhs.total + rhs_num, result.total )

    result = lhs - rhs_res
    self.assertEqual( lhs.total - rhs_num, result.total )

    result = lhs - rhs_num
    self.assertEqual( lhs.total - rhs_num, result.total )

    # result = lhs * rhs_res NOT VALID
    # self.assertEqual( lhs.total - rhs_num, result.total )

    result = lhs * rhs_num
    self.assertEqual( lhs.total * rhs_num, result.total )

    result = lhs / rhs_res
    self.assertEqual( lhs.total / rhs_num, result )
    self.assertIsInstance( result, int )

    result = lhs / rhs_num
    self.assertEqual( lhs.total / rhs_num, result.total )
    self.assertIsInstance( result, res.Resource )

    # Now try in place assignment
    rhs_num = 4096
    rhs_res = res.Resource( "foo", f"4kb" )

    lhs = res.Resource( "foo", "12kb" )
    result = copy.deepcopy( lhs )
    result += rhs_res
    self.assertEqual( lhs.total + rhs_num, result.total )

    result = copy.deepcopy( lhs )
    result += rhs_num
    self.assertEqual( lhs.total + rhs_num, result.total )

    result = copy.deepcopy( lhs )
    result -= rhs_res
    self.assertEqual( lhs.total - rhs_num, result.total )

    result = copy.deepcopy( lhs )
    result -= rhs_num
    self.assertEqual( lhs.total - rhs_num, result.total )

    # result = lhs * rhs_res NOT VALID
    # self.assertEqual( lhs.total - rhs_num, result.total )

    result = copy.deepcopy( lhs )
    result *= rhs_num
    self.assertEqual( lhs.total * rhs_num, result.total )

    result = copy.deepcopy( lhs )
    result /= rhs_res
    self.assertEqual( lhs.total / rhs_num, result )
    self.assertIsInstance( result, int )

    result = copy.deepcopy( lhs )
    result /= rhs_num
    self.assertEqual( lhs.total / rhs_num, result.total )
    self.assertIsInstance( result, res.Resource )

  def test_resource_unsupported_operations( self ):
    """Test ability of resource to catch unsupported operations"""
    rhs_num = 2
    rhs_res = res.Resource( "foo", rhs_num )

    with self.assertRaises( TypeError ):
      lhs = res.Resource( "foo", "nonnumeric" )

    with self.assertRaises( ValueError ):
      lhs = res.Resource( "foo", -1 )

    with self.assertRaises( ValueError ):
      lhs = res.Resource( "foo", "-2kb" )

    lhs = res.Resource( "foo", 4 )
    with self.assertRaises( TypeError ):
      result = lhs * rhs_res

    lhs = res.Resource( "bar", 4 )
    with self.assertRaises( TypeError ):
      result = lhs + rhs_res

    lhs = res.Resource( "foo", "4b" )
    with self.assertRaises( TypeError ):
      result = lhs + rhs_res

    with self.assertRaises( TypeError ):
      result = lhs + 4.1

    with self.assertRaises( TypeError ):
      result = lhs - 4.1

    with self.assertRaises( ValueError ):
      result = lhs - 6

  def test_acquirable_resource( self ):
    """Test standalone creation of an individual usable numeric resource"""
    res.AcquirableResource( "foo", 0 )
    res.AcquirableResource( "foo", "0b" )
    res.AcquirableResource( "foo", "0gb" )
    res.AcquirableResource( "foo", "12gb" )

  def test_acquirable_resource_tracking( self ):
    """Test the ability of a usable resource to keep track of amount in use"""
    rhs_num = 1024
    rhs_res = res.Resource( "foo", "1kb" )

    lhs = res.AcquirableResource( "foo", "4kb" )

    with self.assertRaises( ValueError ):
      result = lhs + rhs_res
    with self.assertRaises( ValueError ):
      result = lhs + rhs_num
    result = lhs - rhs_res
    # An acquirable resource should result in a similar acquirable resource with 
    # the underlying acquirable modified
    self.assertNotEqual( lhs.total - rhs_num, result.total )
    self.assertNotEqual( lhs.acquirable.total, result.acquirable.total )
    self.assertEqual( lhs.total, result.total )
    self.assertEqual( lhs.acquirable.total - rhs_num, result.acquirable.total )

    # Now with in place assignment
    result = copy.deepcopy( lhs )
    with self.assertRaises( ValueError ):
      result += rhs_res
    result = copy.deepcopy( lhs )
    with self.assertRaises( ValueError ):
      result += rhs_num

    result = copy.deepcopy( lhs )
    result -= rhs_res
    # An acquirable resource should result in a similar acquirable resource with 
    # the underlying acquirable modified
    self.assertNotEqual( lhs.total - rhs_num, result.total )
    self.assertNotEqual( lhs.acquirable.total, result.acquirable.total )
    self.assertEqual( lhs.total, result.total )
    self.assertEqual( lhs.acquirable.total - rhs_num, result.acquirable.total )

    rhs_num = 1024*5
    rhs_res = res.Resource( "foo", "5kb" )
    with self.assertRaises( ValueError ):
      result = lhs - rhs_res

    with self.assertRaises( ValueError ):
      result = lhs - rhs_num
    result = copy.deepcopy( lhs )
    with self.assertRaises( ValueError ):
      result -= rhs_res
    result = copy.deepcopy( lhs )
    with self.assertRaises( ValueError ):
      result -= rhs_num
