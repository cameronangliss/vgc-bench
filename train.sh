#!/bin/bash

if [[ $PATH != "/scratch/cluster/cangliss/bin:"* ]]; then
    export PATH="/scratch/cluster/cangliss/bin:$PATH"
fi

run_id=1
team_counts=(1 4 16 64)
ports=(7200 7201 7202 7203)
devices=("cuda:0" "cuda:1" "cuda:2" "cuda:3")

start_showdown() {
    local port=$1
    (
        cd pokemon-showdown
        node pokemon-showdown start $port --no-security > /dev/null 2>&1 &
        echo $!
    )
}

train() {
    local i=$1
    local num_teams="${team_counts[$i]}"
    local port="${ports[$i]}"
    local device="${devices[$i]}"

    echo "Starting Showdown server for training process $i..."
    showdown_pid=$(start_showdown $port)
    sleep 5
    echo "Starting training process $i..."
    python vgc_bench/train.py --run_id $run_id --num_teams $num_teams --port $port --device $device --self_play > "debug$port.log" 2>&1
    exit_status=$?
    if [ $exit_status -ne 0 ]; then
        echo "Training process $i died with exit status $exit_status"
        kill $showdown_pid
        if ! kill -0 $$ 2> /dev/null; then
            return
        fi
        train $i
    else
        echo "Training process $i finished!"
        kill $showdown_pid
    fi
}

trap "echo 'Stopping...'; kill 0" SIGINT
mkdir -p "results$run_id"
for i in "${!team_counts[@]}"; do
    train $i &
    sleep 30
done
wait
