#!/usr/bin/sh

# extract
WHEEL=$( realpath $1 )
EXTRACT=$( mktemp -d )
cd $EXTRACT
unzip $WHEEL

# post processing here
chmod +x sane/action_launcher.py

# repackage, force update
rm $WHEEL
zip -r $WHEEL sane*

cd - && rm $EXTRACT -r
