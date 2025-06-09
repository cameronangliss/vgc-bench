# How to setup
Prerequisites:
1. Python
1. NodeJS and npm (to run the showdown server locally)
1. Git

The newest of each should be fine.

Run the following to ensure that pokemon showdown is configured:
```
git submodule update --init --recursive
cd pokemon-showdown
node pokemon-showdown start --no-security
```
Let that run until you see the following text:
```
RESTORE CHATROOM: lobby
RESTORE CHATROOM: staff
Worker 1 now listening on 0.0.0.0:8000
Test your server at http://localhost:8000
```
Then Ctrl+c the operation and run the following from the root of VGC-Bench:
```
python3 -m venv <env-path>
source <env-path>/bin/activate
pip install -r requirements.txt
python dexter/scrape_data.py
```

# How to run
First, run `node pokemon-showdown start --no-security` from the pokemon-showdown directory in one terminal, and then...
1. Run `python dexter/train.py` to train with RL methods.
1. Run `python dexter/pretrain.py` to train with BC method.
1. Run `python dexter/play.py` to play on the online servers. Run `python dexter/play.py --help` for option details.
1. To scrape logs from showdown, run `python dexter/scrape_logs.py`, or to convert logs to state-action pairs, run `python dexter/logs2trajs.py`.
1. To evaluate agents in cross-play and get ELO ratings, run `python dexter/eval.py` (manual configuration of the file required)

OR

Use the train.sh, pretrain.sh, or eval.sh scripts for a more streamlined experience. Scripts require manual configuration to operate, use --help on executables for more info

# Data
Here's a dataset of Gen 9 VGC battles, all with open team sheets enabled: https://huggingface.co/datasets/cameronangliss/vgc-battle-logs
