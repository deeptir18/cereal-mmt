#!/bin/bash

FOLDER=$2
CONFIG=$1
NUM_CLIENTS=9
#python3 common.py -y $CONFIG -s protobuf -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s protobuf -e depth -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
python3 common.py -y $CONFIG -s flatbuffers -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
python3 common.py -y $CONFIG -s flatbuffers -e depth -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER


