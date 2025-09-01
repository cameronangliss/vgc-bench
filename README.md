# VGC-Bench
This is the official code for the paper [VGC-Bench: A Benchmark for Generalizing Across Diverse Team Strategies in Competitive Pokémon](https://arxiv.org/abs/2506.10326).

This benchmark includes:
- population-based reinforcement learning (RL) with 3 PSRO methods to fine-tune an agent initialized either randomly or with the output of the BC pipeline
- a behavior cloning (BC) pipeline to gather human demonstrations, process them into state-action pairs, and train a model to imitate human play
- a very basic Large Language Model (LLM) player that any LLM can easily be plugged into
- 3 basic heuristic players from [poke-env](https://github.com/hsahovic/poke-env)

# How to setup
Prerequisites:
1. Python (I use v3.12)
1. NodeJS and npm (whatever pokemon-showdown requires)

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
This shows that you can locally host the showdown server.

Install project dependencies by running:
```
pip install .[dev]
```
Setup necessary local data by running:
```
python vgc_bench/scrape_data.py
```

# How to use

NOTE: Unless you're playing against other humans on the online ladder, you must run your own localhost showdown server with `node pokemon-showdown start --no-security` from the pokemon-showdown directory (not necessary if using bash scripts directly).

All .py files in `vgc_bench/` are scripts and (with the exception of [scrape_data.py](vgc_bench/scrape_data.py)) have helpful `--help` text. By contrast, all .py files in `vgc_bench/src/` are not scripts, and are not intended to be run standalone.

## Population-based Reinforcement Learning

The training code offers the following training algorithms:
- pure self-play
- fictitious play
- double oracle method
- policy exploitation

...as well as some special training options:
- configurable frame stacking
- excluding mirror matches (p1 and p2 using the same team)
- starting agent with random teampreview at the beginning of each game

See [train.sh](train.sh) for an example call of train.py (or just configure and run the bash script itself).

## Behavior Cloning

1. [scrape_logs.py](vgc_bench/scrape_logs.py) scrapes logs from the [Pokémon Showdown replay database](https://replay.pokemonshowdown.com) (see [vgc-battle-logs](https://huggingface.co/datasets/cameronangliss/vgc-battle-logs) for a dataset of Gen 9 VGC battles, all with both players agreeing to use open team sheets)
1. [logs2trajs.py](vgc_bench/logs2trajs.py) reads the logs from player 1 and 2's perspective
1. [pretrain.py](vgc_bench/pretrain.py) uses those transitions to train a policy with behavior cloning

NOTE: Both scrape_logs.py and logs2trajs.py have optional parallelization, which are essentially necessary if you're scraping/parsing logs at large scale.

The pretraining code offers some notable options:
- configurable frame stacking
- fraction of dataset to load into memory during behavior cloning at any given time (if not set low enough, can result in OOM)

See [pretrain.sh](pretrain.sh) for an example call of pretrain.py (or just configure and run the bash script itself).

## LLMs

See [llm.py](vgc_bench/src/llm.py) for the provided LLMPlayer wrapper class. We use `meta-llama/Meta-Llama-3.1-8B-Instruct`, but the user may replace logic in the `setup_llm` and `get_response` methods to use a different LLM.

## Heuristics

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

## Evaluation

- [play.py](vgc_bench/play.py) loads a saved policy and plays it against humans either via challenge or the ladder on Pokémon Showdown
- [eval.py](vgc_bench/eval.py) runs the cross-play evaluation, performance test, generalization test, and ranking algorithm as described in our paper (see above)

See [eval.sh](eval.sh) for an example call of [eval.py](vgc_bench/eval.py) (or just configure and run the bash script itself).

# Cite us

```bibtex
@article{angliss2025benchmark,
  title={A Benchmark for Generalizing Across Diverse Team Strategies in Competitive Pok$\backslash$'emon},
  author={Angliss, Cameron and Cui, Jiaxun and Hu, Jiaheng and Rahman, Arrasy and Stone, Peter},
  journal={arXiv preprint arXiv:2506.10326},
  year={2025}
}
```
