# IMPORTANT: Fill in before running
username=""
password=""
reg=""
results_suffix=""

python -m vgc_bench.play \
    --username $username \
    --password $password \
    --reg $reg \
    --run_id 1 \
    --results_suffix $results_suffix \
    --method bc-sp-xm \
    --num_teams 2 \
    -n 1
