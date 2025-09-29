# VGC-Bench
This is the official code for the paper [VGC-Bench: A Benchmark for Generalizing Across Diverse Team Strategies in Competitive Pokémon](https://arxiv.org/abs/2506.10326).

This benchmark includes:
- multi-agent reinforcement learning (RL) with 4 Policy Space Response Oracle (PSRO) algorithms to fine-tune an agent initialized either randomly or with the output of the BC pipeline
- a behavior cloning (BC) pipeline to gather human demonstrations, process them into state-action pairs, and train a model to imitate human play
- a basic Large Language Model (LLM) player that any LLM can easily be plugged into
- 3 heuristic players from [poke-env](https://github.com/hsahovic/poke-env)

# 🛠️ Setup
Prerequisites:
1. Python (I use v3.12)
1. NodeJS and npm (whatever pokemon-showdown requires)

Run the following to ensure that pokemon showdown is configured:
```
git submodule update --init --recursive
cd pokemon-showdown
npm i
node pokemon-showdown start --no-security
```
Let that run until you see the following text:
```
RESTORE CHATROOM: lobby
RESTORE CHATROOM: staff
Worker 1 now listening on 0.0.0.0:8000
Test your server at http://localhost:8000
```
This shows that you can locally host the showdown server.

Install project dependencies by running:
```
pip install .[dev]
```
Setup necessary local data by running:
```
python vgc_bench/scrape_data.py
```

# 👨‍💻 How to use

NOTE: Unless you're playing your policy on the live Pokémon Showdown servers with [play.py](vgc_bench/play.py), you must locally host your own server by running `node pokemon-showdown start <PORT> --no-security` from `pokemon-showdown/` (done automatically if using bash scripts).

All `.py` files in `vgc_bench/` are scripts and (with the exception of [scrape_data.py](vgc_bench/scrape_data.py) and [visualize.py](vgc_bench/visualize.py)) have helpful `--help` text. By contrast, all `.py` files in `vgc_bench/src/` are not scripts, and are not intended to be run standalone.

## 🏆 Population-based Reinforcement Learning

The training code offers the following PSRO algorithms:
- pure self-play
- fictitious play
- double oracle method
- policy exploitation

...as well as some special training options:
- initializing the policy with the output of the BC pipeline (requires manually copying the BC policy file into the training run's save folder)
- frame stacking with specified number of frames
- excluding mirror matches (p1 and p2 using the same team)
- starting agent with random teampreview at the beginning of each game

See [train.sh](train.sh) for running multiple training runs simultaneously with automatic pokemon-showdown server management.

## 📚 Behavior Cloning

1. [scrape_logs.py](vgc_bench/scrape_logs.py) scrapes logs from the [Pokémon Showdown replay database](https://replay.pokemonshowdown.com), automatically filtering out bad logs and only scraping logs with open team sheets (OTS)
    - optional parallelization (strongly recommended)
    - if you don't need logs after 09/20/2025, just download our pre-scraped dataset of logs: [vgc-battle-logs](https://huggingface.co/datasets/cameronangliss/vgc-battle-logs)
1. [logs2trajs.py](vgc_bench/logs2trajs.py) parses the logs into trajectories composed of state-action transitions
    - optional parallelization (strongly recommended)
    - `--min_rating` and `--only_winner` can be used to filter out low-Elo and losing trajectories respectively
1. [pretrain.py](vgc_bench/pretrain.py) uses the gathered trajectories to train a policy with behavior cloning
    - frame stacking with specified number of frames
    - configurable fraction of dataset to load into memory at any given time (if not set low enough, program may run out of memory)
    - see [pretrain.sh](pretrain.sh) for running behavior cloning with automatic pokemon-showdown server management

## 🤖 LLMs

See [llm.py](vgc_bench/src/llm.py) for the provided LLMPlayer wrapper class. We use `meta-llama/Meta-Llama-3.1-8B-Instruct`, but the user may replace logic in the `setup_llm` and `get_response` methods to use a different LLM.

## 🎲 Heuristics

See [poke-env](https://github.com/hsahovic/poke-env) for detailed examples of using the heuristic players. For example:

```python
import asyncio

from poke_env import cross_evaluate
from poke_env.player import MaxBasePowerPlayer, RandomPlayer, SimpleHeuristicsPlayer

random_player = RandomPlayer()
mbp_player = MaxBasePowerPlayer()
sh_player = SimpleHeuristicsPlayer()
results = asyncio.run(cross_evaluate([random_player, mbp_player, sh_player], n_challenges=100))
print(results)
```

## 📊 Evaluation

- [eval.py](vgc_bench/eval.py) runs the cross-play evaluation, performance test, generalization test, and ranking algorithm as described in our paper (see above)
    - see [eval.sh](eval.sh) for running multiple evaluations simultaneously with automatic pokemon-showdown server management
- [play.py](vgc_bench/play.py) loads a saved policy onto the live Pokémon Showdown servers, where the policy can receive challenges from other users or enter the online Elo ladder
- [visualize.py](vgc_bench/visualize.py) processes cross-evaluation results into heatmaps and features conversion functions for LaTeX and Markdown formats

### Cross-evaluation of all AI agents

For each run, 200 battles were used to compare agents, except for LLM player which was compared with 20 battles. The heatmap below averages the results of 5 independent training runs for each trainable agent, accounting for 1000 total battles in each agent comparison, and 100 battles per comparison for the LLM player.

![figures/heatmaps_avg.png](figures/heatmaps_avg.png)

Legend: R = random player, MBP = max base power player, SH = simple heuristics player, LLM = LLM player, SP = self-play agent, FP = fictitious play agent, DO = double oracle agent, BC = behavior cloning agent, BCSP = self-play agent initialized with behavior cloning, BCFP = fictitious play agent initialized with behavior cloning, BCDO = double oracle agent initialized with behavior cloning

### Performance Test

This test compares the performance of the strongest method on average across runs 1-5 of the 1, 4, 16, and 64 team setting with the one team that they all had training exposure to.

| # teams   | 1 (BCSP) | 4 (BCSP) | 16 (BCDO) | 64 (BCSP) |
|-----------|----------|----------|-----------|-----------|
| 1 (BCSP)  | --       | 0.699    | 0.74      | 0.698     |
| 4 (BCSP)  | 0.301    | --       | 0.594     | 0.672     |
| 16 (BCDO) | 0.26     | 0.406    | --        | 0.644     |
| 64 (BCSP) | 0.302    | 0.328    | 0.356     | --        |

### Generalization Test

This test compares the performance of the strongest method on average across runs 1-5 of the 1, 4, 16, and 64 team setting with 72 teams that none of them had training exposure to.

| # teams   | 1 (BCSP) | 4 (BCSP) | 16 (BCDO) | 64 (BCSP) |
|-----------|----------|----------|-----------|-----------|
| 1 (BCSP)  | --       | 0.405    | 0.375     | 0.331     |
| 4 (BCSP)  | 0.595    | --       | 0.453     | 0.422     |
| 16 (BCDO) | 0.625    | 0.547    | --        | 0.436     |
| 64 (BCSP) | 0.669    | 0.578    | 0.564     | --        |

See our paper for further results and details.

# 📜 Cite us

```bibtex
@article{angliss2025benchmark,
  title={A Benchmark for Generalizing Across Diverse Team Strategies in Competitive Pok$\backslash$'emon},
  author={Angliss, Cameron and Cui, Jiaxun and Hu, Jiaheng and Rahman, Arrasy and Stone, Peter},
  journal={arXiv preprint arXiv:2506.10326},
  year={2025}
}
```
