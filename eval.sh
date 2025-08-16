#!/bin/bash

if [[ $PATH != "/scratch/cluster/cangliss/bin:"* ]]; then
    export PATH="/scratch/cluster/cangliss/bin:$PATH"
fi
export HF_HOME=/scratch/cluster/cangliss/hf_cache

team_counts=(1 4 16 64)
team_lists=("30 31" "32 33" "30")
ports=(8000 8001 8002 8003)
devices=("cuda:0" "cuda:1" "cuda:2" "cuda:3")

start_showdown() {
    local port=$1
    (
        cd pokemon-showdown
        node pokemon-showdown start "$port" --no-security > /dev/null 2>&1 &
        echo $!
    )
}

start_eval() {
    local i=$1
    local num_teams=${team_counts[$i]}
    local team_indices=${team_lists[$i]}
    local port=${ports[$i]}
    local device=${devices[$i]}

    echo "Starting Showdown server for pretraining process..."
    showdown_pid=$(start_showdown "$port")
    sleep 5
    echo "Starting evaluation..."
    python vgc_bench/eval.py --num_teams "$num_teams" --port "$port" --device "$device" > debug"$port".log 2>&1
    exit_status=$?
    if [ $exit_status -ne 0 ]; then
        echo "Evaluation process died with exit status $exit_status"
    fi
    kill $showdown_pid
}

for i in "${!team_counts[@]}"; do
    start_eval "$i" &
    sleep 10
done
wait
