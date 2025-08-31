#!/bin/bash

if [[ $PATH != "/scratch/cluster/cangliss/bin:"* ]]; then
    export PATH="/scratch/cluster/cangliss/bin:$PATH"
fi

run_ids=(1 1 1 1)
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
    local run_id="${run_ids[$i]}"
    local num_teams="${team_counts[$i]}"
    local port="${ports[$i]}"
    local device="${devices[$i]}"

    mkdir -p "results$run_id"
    echo "Starting Showdown server for training process $i..."
    showdown_pid=$(start_showdown $port)
    sleep 5
    echo "Starting training process $i..."
    python vgc_bench/train.py --run_id $run_id --num_teams $num_teams --num_envs 24 --port $port --device $device --self_play > "debug$port.log" 2>&1
    exit_status=$?
    if [ $exit_status -ne 0 ]; then
        echo "Training process $i died with exit status $exit_status"
    else
        echo "Training process $i finished!"
    fi
    kill $showdown_pid
}

trap "echo 'Stopping...'; kill 0" SIGINT
for i in "${!run_ids[@]}"; do
    train $i &
    sleep 30
done
wait
