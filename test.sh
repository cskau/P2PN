#!/usr/bin/env bash

# setup seed peer
./discover.py p8000 8000 >&- & # start in background

for (( c = 8001; c <= 8030; c++ )); do
  ./discover.py p$c $c >&- & # start in background
done


# wait for peers to come up before connection to them
sleep 1

for (( c = 8001; c <= 8030; c++ )); do
  sleep 1
  echo "hello http://localhost:8000" | ./discover.py --interactive $c
done

# wait for peers to come up before connection to them
sleep 1

# start interactive
./discover.py --interactive 8000

# kill all spawned processes
kill `jobs -p`
