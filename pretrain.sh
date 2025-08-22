#!/bin/bash

if [[ $PATH != "/scratch/cluster/cangliss/bin:"* ]]; then
    export PATH="/scratch/cluster/cangliss/bin:$PATH"
fi

run_id=1
num_teams=136
port=8004
device="cuda:0"

start_showdown() {
    local port=$1
    (
        cd pokemon-showdown
        node pokemon-showdown start "$port" --no-security > /dev/null 2>&1 &
        echo $!
    )
}

mkdir -p "results$run_id"
echo "Starting Showdown server for pretraining process..."
showdown_pid=$(start_showdown "$port")
echo "Starting pretraining process..."
python vgc_bench/pretrain.py --run_id $run_id --num_teams "$num_teams" --port "$port" --device "$device"
exit_status=$?
if [ $exit_status -ne 0 ]; then
    echo "Pretraining process died with exit status $exit_status"
fi
kill $showdown_pid
