#!/bin/bash

if [[ $PATH != "/scratch/cluster/cangliss/bin:"* ]]; then
    export PATH="/scratch/cluster/cangliss/bin:$PATH"
fi

team_counts=(1 3 10 30)
team_lists=("30 31" "32 33" "30")
ports=(7200 7201 7202 7203)
devices=("cuda:0" "cuda:1" "cuda:2" "cuda:3")

start_showdown() {
    local port=$1
    (
        cd pokemon-showdown
        node pokemon-showdown start "$port" --no-security > /dev/null 2>&1 &
        echo $!
    )
}

start_training() {
    local i=$1
    local num_teams=${team_counts[$i]}
    local team_indices=${team_lists[$i]}
    local port=${ports[$i]}
    local device=${devices[$i]}

    echo "Starting Showdown server for training process $i..."
    showdown_pid=$(start_showdown "$port")
    sleep 5
    echo "Starting training process $i..."
    python vgc_bench/train.py --num_teams "$num_teams" --port "$port" --device "$device" --self_play > debug"$port".log 2>&1
    exit_status=$?
    if [ $exit_status -ne 0 ]; then
        echo "Training process $i died with exit status $exit_status"
    fi
    kill $showdown_pid
}

if [ ! -d results ]; then
    mkdir -p results
fi
while true; do
    for i in "${!team_counts[@]}"; do
        start_training "$i" &
        sleep 10
    done
    wait
    sleep 10
done
