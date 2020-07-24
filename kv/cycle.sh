#!/bin/bash

CONFIG=$1 # echo-test.yaml
LOGS=$2 # where to put out logs
YC=$3 # yc root file
NUM_CLIENTS=9
LIBOS="dmtr-lwip"

python3 common.py -y $CONFIG -yc $YC -s handcrafted -n $NUM_CLIENTS -o $LIBOS -l $LOGS
python3 common.py -y $CONFIG -yc $YC -s capnproto -n $NUM_CLIENTS -o $LIBOS -l $LOGS
python3 common.py -y $CONFIG -yc $YC -s flatbuffers -n $NUM_CLIENTS -o $LIBOS -l $LOGS
python3 common.py -y $CONFIG -yc $YC -s protobuf -n $NUM_CLIENTS -o $LIBOS -l $LOGS
