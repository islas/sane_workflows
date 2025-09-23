#!/usr/bin/sh
script=$1
if [ -z "$script" ] || [ ! -f $script ]; then
  echo "No executable script provided" >&2
  exit 1
fi

save_env=$( mktemp tmp_env.XXXXXXXX )
output=$( env )

parse_env=$( cat << EOF
env     = {}
curr_open = 0
var = None
val = ""
for line in env_str.splitlines():
  val += "\n" + line
  if curr_open == 0:
    var, val = line.split( "=", maxsplit=1 )
    # print( f"Parsing {var}" )

  if ( val[0:2] == "()" and curr_open == 0 ) or curr_open > 0:
    source = line
    if ( val[0:2] == "()" and curr_open == 0 ):
      source = val

    curr_open += source.count( "{" )
    curr_open -= source.count( "}" )
    # print( f"Tracking {var} open braces {curr_open} after this line" )


  if curr_open == 0:
    # print( f"Finished parsing {var}" )
    env[var] = f"""{val}"""
    val = ""

# pprint.pprint( env, indent=2 )
EOF
)

python3 << EOF
env_str = """$output"""
$parse_env
import json
json.dump( env, open( "$save_env", "w" ), indent=2 )
EOF

. $script

output=$( env )
python3 << EOF
env_str = """$output"""
$parse_env
import json
prev_env = json.load( open( "$save_env", "r" ) )
# print( set( prev_env.items() ) ^ set( env.items() ) )
mod_env = {}
for item in set( prev_env.items() ) ^ set( env.items() ):
  if item in env.items():
    mod_env[item[0]] = item[1]
  elif item[0] not in env:
    mod_env[item[0]] = None

for key, val in mod_env.items():
  if val is not None:
    print( f"os.environ[\"{key}\"] = \"\"\"{val}\"\"\"" )
  else:
    print( f"os.environ.pop( \"{key}\", {val} )" )
EOF

rm $save_env
exit 0
