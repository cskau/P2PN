#!/usr/bin/env bash

NODES=30
PORT=8000

# dynamic vars
PORT_FROM=$(($PORT + 1))
PORT_TO=$(($PORT + $NODES))

# setup seed peer
./discover.py p$PORT $PORT >&- & # start in background

for (( c = $PORT_FROM; c <= $PORT_TO; c++ )); do
  ./discover.py p$c $c >&- & # start in background
done


# wait for seed peer to come up before connecting to them
sleep 1

for (( c = $PORT_FROM; c <= $PORT_TO; c++ )); do
  sleep 1
  echo "hello http://localhost:$PORT" | ./discover.py --interactive $c
done

# wait for peers to come up before connecting to them
sleep 1

# start interactive
./discover.py --interactive $PORT

# kill all spawned processes
kill `jobs -p`
