#!/usr/bin/env bash

NODES=10
PORT=8000
CAP=10

START="["
END="]"
ADRESSES=""

# dynamic vars
PORT_FROM=$(($PORT + 1))
PORT_TO=$(($PORT + $NODES))

mkdir ./logs

echo "Setting up root.."
# setup seed peer in the background
python -u ./discover.py p$PORT $PORT $CAP &> ./logs/$PORT.log &

echo "Setting up $NODES nodes.."
for (( c = $PORT_FROM; c <= $PORT_TO; c++ )); do
  python -u ./discover.py p$c $c $CAP &> ./logs/$c.log & # start in background
done


# wait for seed peer to come up before connecting to them
sleep 1

echo "Connecting nodes.."
for (( c = $PORT_FROM; c <= $PORT_TO; c++ )); do
  echo "hello http://localhost:$PORT" | ./discover.py --interactive $c &> /dev/null
  sleep 1
done

sleep 10

echo "Testing nodes.."
for (( c = $PORT_FROM; c <= $PORT_TO; c++ )); do
  ADRESSES=`python -c "print ','.join([('\"http://localhost:%i\"' % i) for i in range($(($PORT_FROM - 1)), $(($PORT_TO + 1))) if i != $c])"`
  ./discover.py --test $c localhost $START$ADRESSES$END
done

# wait for peers to come up before connecting to them
sleep 1

# start interactive
./discover.py --interactive $PORT

#./discover.py --interactive 8004

bash

# kill all spawned processes
kill `jobs -p`
