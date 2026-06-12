#!/usr/bin/sh
CURRENT_SOURCE_DIR=$( CDPATH= cd -- "$(dirname -- "$0")" && pwd )
PERIOD=$1

QUEUE_DIR=$CURRENT_SOURCE_DIR/queue
COMPLETE_DIR=$CURRENT_SOURCE_DIR/complete

rm -f $CURRENT_SOURCE_DIR/queue/*
rm -f $CURRENT_SOURCE_DIR/complete/*
rm -f $CURRENT_SOURCE_DIR/kill

if [ -z "$PERIOD" ]; then
  PERIOD=5
fi

while [ ! -f $CURRENT_SOURCE_DIR/kill ]; do
  queue=$( ls $QUEUE_DIR )
  for cmd_file in $queue; do
    # echo "Executing ${QUEUE_DIR}/${cmd_file}"
    deps=$( head -n 1 $QUEUE_DIR/$cmd_file | tr ':' ' ' | sed  's/[^0-9 ]//g' )

    ok="true"
    if [ -n "$deps" ]; then
      for d in $deps; do
        if [ ! -f $COMPLETE_DIR/$d ]; then
          ok="false"
        fi
      done
    fi

    if [ "$ok" != "true" ]; then
      continue
    fi

    cmd=$( tail -n 1 $QUEUE_DIR/$cmd_file )
    eval "$cmd" &> /dev/null
    result=$?
    rm $QUEUE_DIR/$cmd_file
    echo $result > $COMPLETE_DIR/$cmd_file
  done
  sleep $PERIOD
done

rm -f $CURRENT_SOURCE_DIR/queue/*
rm -f $CURRENT_SOURCE_DIR/complete/*
rm -f $CURRENT_SOURCE_DIR/kill
