#!/usr/bin/env bash

NODES=10
PORT=8000
CAP=10

START="["
END="]"
ADRESSES=""

# range from which to draw the random neighbour capacities
CAPACITY_FROM=1
CAPACITY_TO=10

# dynamic vars
PORT_FROM=$(($PORT + 1))
PORT_TO=$(($PORT + $NODES))


getRandomInRange() {
  echo $((($RANDOM % $2) + $1))
}


mkdir ./logs

echo "Setting up root.."
# setup seed peer in the background
CAPACITY=$(getRandomInRange $CAPACITY_FROM $CAPACITY_TO)
python -u ./discover.py p$PORT $PORT $CAPACITY &> ./logs/$PORT.log &

echo "Setting up $NODES nodes.."
for (( c = $PORT_FROM; c <= $PORT_TO; c++ )); do
  CAPACITY=$(getRandomInRange $CAPACITY_FROM $CAPACITY_TO)
  python -u ./discover.py p$c $c $CAPACITY &> ./logs/$c.log & # start in background
done


# wait for seed peer to come up before connecting to them
sleep 1

echo "Connecting nodes.."
for (( c = $PORT_FROM; c <= $PORT_TO; c++ )); do
  echo "hello http://localhost:$PORT" | ./discover.py --interactive $c &> /dev/null
done

sleep 10

echo "Testing nodes.."
for (( c = $PORT_FROM; c <= $PORT_TO; c++ )); do
  ADRESSES=`python -c "print ','.join([('\"http://localhost:%i\"' % i) for i in range($(($PORT_FROM - 1)), $(($PORT_TO + 1))) if i != $c])"`
  ./discover.py --test $c localhost $START$ADRESSES$END
done

sleep 1

echo "More dots!!"
for (( c = $PORT_FROM; c <= $PORT_TO; c++ )); do
  echo "nlist -o ./dots/g$PORT.dot" | ./discover.py --interactive $c &> /dev/null
done
dot -O -Tpng ./dots/*.dot

sleep 1

# start interactive
./discover.py --interactive $PORT

#./discover.py --interactive 8004

bash


# kill all spawned processes
kill `jobs -p`
