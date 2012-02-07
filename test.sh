#!/usr/bin/env bash

NODES=4
PORT=8000
CAP=10

# dynamic vars
PORT_FROM=$(($PORT + 1))
PORT_TO=$(($PORT + $NODES))

mkdir ./logs

# setup seed peer in the background
python -u ./discover.py p$PORT $PORT $CAP &>> ./logs/$PORT.log &

for (( c = $PORT_FROM; c <= $PORT_TO; c++ )); do
  python -u ./discover.py p$c $c $CAP &>> ./logs/$c.log & # start in background
done


# wait for seed peer to come up before connecting to them
sleep 1

for (( c = $PORT_FROM; c <= $PORT_TO; c++ )); do
  sleep 1
  echo "hello http://localhost:$PORT" | ./discover.py --interactive $c &> /dev/null
  echo "test http://localhost:$PORT" | ./discover.py --test $c &> /dev/null
done

# wait for peers to come up before connecting to them
sleep 1

# start interactive
./discover.py --interactive $PORT

./discover.py --interactive 8001

# kill all spawned processes
kill `jobs -p`
