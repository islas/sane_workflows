#!/usr/bin/sh
CURRENT_SOURCE_DIR=$( CDPATH= cd -- "$(dirname -- "$0")" && pwd )
QUEUE_DIR=$CURRENT_SOURCE_DIR/queue
COMPLETE_DIR=$CURRENT_SOURCE_DIR/complete

RAW=$*
CMD=${RAW#*--}
ARGS=${RAW%%--*}
id=$( find $QUEUE_DIR/ $COMPLETE_DIR/ -type f | wc -l )

echo "Launching job $id with args \"$ARGS\""
echo "  $CMD"
echo -e "$ARGS\n$CMD" > $QUEUE_DIR/$id
