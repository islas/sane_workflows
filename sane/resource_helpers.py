import re


# Format using PBS-stye
# http://docs.adaptivecomputing.com/torque/4-1-3/Content/topics/2-jobs/requestingRes.htm
_res_size_regex_str = r"(?P<numeric>\d+)(?P<multi>(?P<scale>k|m|g|t)?(?P<unit>b|w)?)"
_res_size_regex     = re.compile( _res_size_regex_str, re.I )
_multipliers    = { "" : 1, "k" : 1024, "m" : 1024**2, "g" : 1024**3, "t" : 1024**4 }


def res_size_dict( resource ) :
  match = _res_size_regex.match( resource )

  if match is not None :
    return { k : ( v.lower() if v is not None else "" ) for k, v in match.groupdict().items() }
  else :
    return None


def res_size_base( res_dict ) :
  return _multipliers[ res_dict["scale" ] ] * int( res_dict["numeric"] )


def res_size_str( res_dict ) :
  size_fmt = "{num}{scale}{unit}"
  return size_fmt.format(
                          num=res_dict["numeric"],
                          scale=res_dict[ "scale" ] if res_dict[ "scale" ] else "",
                          unit=res_dict["unit"]
                          )


def res_size_expand( res_dict ) :

  expanded_dict = {
                    "numeric" : _multipliers[ res_dict["scale" ] ] * int( res_dict["numeric"] ),
                    "scale" : "",
                    "unit" : res_dict["unit"]
                  }
  return expanded_dict


def res_size_reduce( res_dict ) :
  total = res_size_base( res_dict )

  # Convert to simplified size, round up if needed
  log2 = math.log( total, 2 )
  scale = None
  if log2 > 30.0 :
    # Do it in gibi
    scale = "g"
  elif log2 > 20.0 :
    # mebi
    scale = "m"
  elif log2 > 10.0 :
    # kibi
    scale = "k"

  reduced_dict = {
                    "numeric" : math.ceil( total / float( _multipliers[ scale ] ) ),
                    "scale"   : scale,
                    "unit"    : res_dict["unit"]
                  }
  return reduced_dict
