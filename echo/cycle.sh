#!/bin/bash

FOLDER=$2
CONFIG=$1
NUM_CLIENTS=6
#python3 common.py -y $CONFIG -s baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s malloc_baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s capnproto -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s flatbuffers -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s protobytes -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s protobytes -e depth -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s protobuf -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s protobuf -e depth -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s protobytes -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s protobytes -e depth -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s flatbuffers -e depth -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s capnproto -e depth -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s baseline malloc_baseline malloc_no_str memcpy single_memcpy flatbuffers -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
python3 common.py -y $CONFIG -s baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER --segments 1
python3 common.py -y $CONFIG -s baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER --segments 2
python3 common.py -y $CONFIG -s baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER --segments 4
python3 common.py -y $CONFIG -s baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER --segments 8
python3 common.py -y $CONFIG -s baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER --segments 16
#python3 common.py -y $CONFIG -s baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER --segments 20
python3 common.py -y $CONFIG -s baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER --segments 32
python3 common.py -y $CONFIG -s baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER --segments 60
#python3 common.py -y $CONFIG -s baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER --segments 128
#python3 common.py -y $CONFIG -s baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER --segments 256
#python3 common.py -y $CONFIG -s baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER --segments 1

