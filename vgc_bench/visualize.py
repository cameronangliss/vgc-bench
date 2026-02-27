"""
Visualization module for VGC-Bench.

Generates heatmap visualizations and table outputs (LaTeX, Markdown) for
cross-evaluation payoff matrices comparing different agent types across
varying team counts.
"""

import matplotlib.pyplot as plt
import numpy as np

# Data definitions
algos = ["R", "MBP", "SH", "LLM", "SP", "FP", "DO", "BC", "BCSP", "BCFP", "BCDO"]
titles = ["1 team", "4 teams", "16 teams", "64 teams"]

data_list = [  # fill in with actual data matrices
    np.array([]),
    np.array([]),
    np.array([]),
    np.array([]),
]


def matrix_to_latex(matrix, table_idx):
    """Convert a matrix into a LaTeX tabular environment."""
    n = matrix.shape[0]
    header = " & " + " & ".join([algos[i] for i in range(n)]) + " \\\\ \\hline"
    rows = []
    for i in range(n):
        row = [algos[i]]
        for j in range(n):
            val = matrix[i, j]
            row.append("--" if np.isnan(val) else f"{val:.3f}")
        rows.append(" & ".join(row) + " \\\\")
    table = (
        f"\\begin{{table}}[h]\n"
        f"\\centering\n"
        f"\\begin{{tabular}}{{|c|{'c|' * n}}}\n"
        f"\\hline\n"
        f"{header}\n" + "\n".join(rows) + "\n\\hline\n\\end{tabular}\n"
        f"\\caption{{Payoff Matrix {titles[table_idx]}}}\n"
        f"\\end{{table}}\n"
    )
    return table


def matrix_to_markdown(matrix, table_idx):
    """Convert a matrix into a Markdown table."""
    n = matrix.shape[0]
    header = "|     | " + " | ".join([algos[i] for i in range(n)]) + " |"
    separator = "|" + "-----|" * (n + 1)
    rows = []
    for i in range(n):
        row = [algos[i]]
        for j in range(n):
            val = matrix[i, j]
            row.append("--" if np.isnan(val) else f"{val}")
        rows.append("| " + " | ".join(row) + " |")
    table = f"## {titles[table_idx]}\n" + "\n".join([header, separator] + rows) + "\n"
    return table


for i, data in enumerate(data_list):
    print(matrix_to_latex(data, i))
    print(matrix_to_markdown(data, i))

fig, axes = plt.subplots(
    1,
    4,
    figsize=(16, 4),
    gridspec_kw={"left": 0.05, "right": 0.88, "hspace": 0.2, "wspace": 0.3},
)
vmin, vmax = 0, 1
im = None
for ax, data, title in zip(axes.flat, data_list, titles):
    masked = np.ma.masked_invalid(data)
    im = ax.imshow(masked, vmin=vmin, vmax=vmax)
    ax.set_title(title)
    ax.set_xticks(range(len(algos)))
    ax.set_xticklabels(algos, rotation=45, ha="center", rotation_mode="anchor")
    ax.tick_params(axis="x", pad=10)
    ax.set_yticks(range(len(algos)))
    ax.set_yticklabels(algos)
    ax.grid(False)

cbar_ax = fig.add_axes((0.92, 0.1, 0.02, 0.75))
assert im is not None
fig.colorbar(im, cax=cbar_ax, label="Win Rate")

plt.savefig("heatmaps.png")
