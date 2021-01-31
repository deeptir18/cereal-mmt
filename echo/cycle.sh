#!/bin/bash

FOLDER=$2
CONFIG=$1
NUM_CLIENTS=48
#python3 common.py -y $CONFIG -s malloc_baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s capnproto -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s protobuf -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
python3 common.py -y $CONFIG -s flatbuffers -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s protobytes -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s protobytes -e depth -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s protobuf -e depth -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s protobytes -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s protobytes -e depth -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s flatbuffers -e depth -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s capnproto -e depth -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s baseline malloc_baseline malloc_no_str memcpy single_memcpy flatbuffers -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER --segments 1 --zero_copy
#python3 common.py -y $CONFIG -s cornflakes -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER
#python3 common.py -y $CONFIG -s baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER --segments 2 --zero_copy
#python3 common.py -y $CONFIG -s baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER --segments 4 --zero_copy
#python3 common.py -y $CONFIG -s baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER --segments 8 --zero_copy
#python3 common.py -y $CONFIG -s baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER --segments 16 --zero_copy
#python3 common.py -y $CONFIG -s baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER --segments 20
#python3 common.py -y $CONFIG -s baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER --segments 32 --zero_copy
#python3 common.py -y $CONFIG -s baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER --segments 40 --zero_copy
#python3 common.py -y $CONFIG -s baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER --segments 60 --zero_copy
#python3 common.py -y $CONFIG -s baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER --segments 128
#python3 common.py -y $CONFIG -s baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER --segments 256
#python3 common.py -y $CONFIG -s baseline -e size -n $NUM_CLIENTS -o dmtr-lwip -l $FOLDER --segments 1

