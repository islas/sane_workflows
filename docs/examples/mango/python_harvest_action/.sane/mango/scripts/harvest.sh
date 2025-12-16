#!/usr/bin/bash
echo "Harvesting mangos..."
echo -ne "Collected : "
awk 'BEGIN { sum=0 } { sum+=$1 } END { print sum }' mango_tree_*.txt
