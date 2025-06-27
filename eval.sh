#!/bin/bash

if [[ $PATH != "/scratch/cluster/cangliss/bin:"* ]]; then
    export PATH="/scratch/cluster/cangliss/bin:$PATH"
fi
export HF_HOME=/scratch/cluster/cangliss/hf_cache

port=8004
num_teams=1

start_showdown() {
    local port=$1
    (
        cd pokemon-showdown
        node pokemon-showdown start "$port" --no-security > /dev/null 2>&1 &
        echo $!
    )
}

echo "Starting Showdown server for pretraining process..."
showdown_pid=$(start_showdown "$port")
echo "Starting evaluation..."
python vgc_bench/eval.py --num_teams "$num_teams" --port "$port"
exit_status=$?
if [ $exit_status -ne 0 ]; then
    echo "Evaluation process died with exit status $exit_status"
fi
kill $showdown_pid
