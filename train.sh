#!/bin/bash

run_ids=(1 1 1 1)
team_counts=(1 4 16 64)
ports=(7200 7201 7202 7203)
devices=("cuda:0" "cuda:1" "cuda:2" "cuda:3")
total_steps=$((1000 * 98304))  # 98304 is the number of steps per save during training

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

    echo "Starting Showdown server for training process $i..."
    showdown_pid=$(start_showdown $port)
    sleep 5
    echo "Starting training process $i..."
    python -m vgc_bench.train \
        --run_id $run_id \
        --num_teams $num_teams \
        --num_envs 24 \
        --num_eval_workers 24 \
        --port $port \
        --device $device \
        --behavior_clone \
        --self_play \
        --total_steps "$total_steps" \
        > "debug$port.log" 2>&1
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
