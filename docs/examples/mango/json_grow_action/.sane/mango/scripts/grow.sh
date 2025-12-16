#!/usr/bin/bash
NTREES=$1
echo "Growing with $NTREES trees with $GROWTH_RATE% growth rate..."

for i in $(seq 1 $NTREES ); do
  NMANGOS=$(( ($RANDOM % 10) * $GROWTH_RATE / 100 + 1 ))
  echo "  Tree $i grew $NMANGOS mangos!"
  echo $NMANGOS > mango_tree_$i.txt
done
