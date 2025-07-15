#!/usr/bin/sh

framework_directory=$1
action_config=$2

echo "Moving to $framework_directory"
cd $framework_directory
echo "Executing action with config $action_config..."
./action_launcher.py $action_config
