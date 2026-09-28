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

# Stage outside the queue so the runner only sees complete entries.
printf '%s\n%s\n' "$ARGS" "$CMD" > "$CURRENT_SOURCE_DIR/$id.queue.tmp"
mv "$CURRENT_SOURCE_DIR/$id.queue.tmp" "$QUEUE_DIR/$id"
