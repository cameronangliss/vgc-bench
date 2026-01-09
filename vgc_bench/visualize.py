import matplotlib.pyplot as plt
import numpy as np

# Data definitions
algos = ["R", "MBP", "SH", "LLM", "SP", "FP", "DO", "BC", "BCSP", "BCFP", "BCDO"]
titles = ["1 team", "4 teams", "16 teams", "64 teams"]

data_list = [
    np.array(
        [
            [
                np.nan,
                0.068,
                0.039,
                0.22,
                0.007,
                0.014,
                0.008,
                0.053,
                0.001,
                0.002,
                0.012,
            ],
            [0.932, np.nan, 0.298, 0.66, 0.134, 0.07, 0.116, 0.44, 0.064, 0.05, 0.136],
            [
                0.961,
                0.702,
                np.nan,
                0.82,
                0.215,
                0.196,
                0.229,
                0.551,
                0.11,
                0.091,
                0.178,
            ],
            [0.78, 0.34, 0.18, np.nan, 0.11, 0.08, 0.07, 0.31, 0.02, 0.02, 0.06],
            [
                0.993,
                0.866,
                0.785,
                0.89,
                np.nan,
                0.587,
                0.707,
                0.79,
                0.229,
                0.432,
                0.448,
            ],
            [
                0.986,
                0.93,
                0.804,
                0.92,
                0.413,
                np.nan,
                0.482,
                0.805,
                0.229,
                0.239,
                0.266,
            ],
            [
                0.992,
                0.884,
                0.771,
                0.93,
                0.293,
                0.518,
                np.nan,
                0.842,
                0.203,
                0.236,
                0.337,
            ],
            [0.947, 0.56, 0.449, 0.69, 0.21, 0.195, 0.158, np.nan, 0.048, 0.025, 0.126],
            [0.999, 0.936, 0.89, 0.98, 0.771, 0.771, 0.797, 0.952, np.nan, 0.51, 0.744],
            [0.998, 0.95, 0.909, 0.98, 0.568, 0.761, 0.764, 0.975, 0.49, np.nan, 0.556],
            [
                0.988,
                0.864,
                0.822,
                0.94,
                0.552,
                0.734,
                0.663,
                0.874,
                0.256,
                0.444,
                np.nan,
            ],
        ]
    ),
    np.array(
        [
            [
                np.nan,
                0.079,
                0.041,
                0.21,
                0.016,
                0.023,
                0.013,
                0.036,
                0.003,
                0.002,
                0.007,
            ],
            [
                0.921,
                np.nan,
                0.369,
                0.76,
                0.187,
                0.182,
                0.176,
                0.407,
                0.091,
                0.094,
                0.098,
            ],
            [
                0.959,
                0.631,
                np.nan,
                0.75,
                0.289,
                0.262,
                0.302,
                0.518,
                0.132,
                0.143,
                0.133,
            ],
            [0.79, 0.24, 0.25, np.nan, 0.14, 0.06, 0.08, 0.29, 0.06, 0.03, 0.02],
            [
                0.984,
                0.813,
                0.711,
                0.86,
                np.nan,
                0.513,
                0.488,
                0.671,
                0.246,
                0.239,
                0.263,
            ],
            [
                0.977,
                0.818,
                0.738,
                0.94,
                0.487,
                np.nan,
                0.569,
                0.647,
                0.273,
                0.293,
                0.253,
            ],
            [
                0.987,
                0.824,
                0.698,
                0.92,
                0.512,
                0.431,
                np.nan,
                0.653,
                0.222,
                0.256,
                0.213,
            ],
            [
                0.964,
                0.593,
                0.482,
                0.71,
                0.329,
                0.353,
                0.347,
                np.nan,
                0.13,
                0.114,
                0.171,
            ],
            [
                0.997,
                0.909,
                0.868,
                0.94,
                0.754,
                0.727,
                0.778,
                0.87,
                np.nan,
                0.523,
                0.505,
            ],
            [
                0.998,
                0.906,
                0.857,
                0.97,
                0.761,
                0.707,
                0.744,
                0.886,
                0.477,
                np.nan,
                0.522,
            ],
            [
                0.993,
                0.902,
                0.867,
                0.98,
                0.737,
                0.747,
                0.787,
                0.829,
                0.495,
                0.478,
                np.nan,
            ],
        ]
    ),
    np.array(
        [
            [np.nan, 0.067, 0.052, 0.27, 0.04, 0.037, 0.032, 0.038, 0.01, 0.003, 0.005],
            [
                0.933,
                np.nan,
                0.337,
                0.68,
                0.31,
                0.272,
                0.274,
                0.361,
                0.104,
                0.089,
                0.084,
            ],
            [
                0.948,
                0.663,
                np.nan,
                0.77,
                0.413,
                0.358,
                0.432,
                0.478,
                0.152,
                0.16,
                0.147,
            ],
            [0.73, 0.32, 0.23, np.nan, 0.2, 0.11, 0.14, 0.21, 0.07, 0.08, 0.02],
            [0.96, 0.69, 0.587, 0.8, np.nan, 0.479, 0.474, 0.551, 0.209, 0.208, 0.241],
            [
                0.963,
                0.728,
                0.642,
                0.89,
                0.521,
                np.nan,
                0.486,
                0.578,
                0.211,
                0.232,
                0.216,
            ],
            [0.968, 0.726, 0.568, 0.86, 0.526, 0.514, np.nan, 0.533, 0.228, 0.215, 0.2],
            [
                0.962,
                0.639,
                0.522,
                0.79,
                0.449,
                0.422,
                0.467,
                np.nan,
                0.204,
                0.191,
                0.193,
            ],
            [
                0.99,
                0.896,
                0.848,
                0.93,
                0.791,
                0.789,
                0.772,
                0.796,
                np.nan,
                0.498,
                0.481,
            ],
            [
                0.997,
                0.911,
                0.84,
                0.92,
                0.792,
                0.768,
                0.785,
                0.809,
                0.502,
                np.nan,
                0.486,
            ],
            [0.995, 0.916, 0.853, 0.98, 0.759, 0.784, 0.8, 0.807, 0.519, 0.514, np.nan],
        ]
    ),
    np.array(
        [
            [np.nan, 0.081, 0.029, 0.21, 0.054, 0.053, 0.066, 0.05, 0.008, 0.01, 0.006],
            [
                0.919,
                np.nan,
                0.344,
                0.67,
                0.386,
                0.388,
                0.407,
                0.398,
                0.122,
                0.127,
                0.117,
            ],
            [
                0.971,
                0.656,
                np.nan,
                0.79,
                0.486,
                0.482,
                0.49,
                0.511,
                0.166,
                0.173,
                0.199,
            ],
            [0.79, 0.33, 0.21, np.nan, 0.24, 0.12, 0.19, 0.15, 0.06, 0.04, 0.03],
            [
                0.946,
                0.614,
                0.514,
                0.76,
                np.nan,
                0.512,
                0.51,
                0.481,
                0.169,
                0.189,
                0.196,
            ],
            [0.947, 0.612, 0.518, 0.88, 0.488, np.nan, 0.487, 0.466, 0.198, 0.18, 0.16],
            [0.934, 0.593, 0.51, 0.81, 0.49, 0.513, np.nan, 0.508, 0.197, 0.189, 0.198],
            [
                0.95,
                0.602,
                0.489,
                0.85,
                0.519,
                0.534,
                0.492,
                np.nan,
                0.231,
                0.234,
                0.238,
            ],
            [
                0.992,
                0.878,
                0.834,
                0.94,
                0.831,
                0.802,
                0.803,
                0.769,
                np.nan,
                0.554,
                0.505,
            ],
            [0.99, 0.873, 0.827, 0.96, 0.811, 0.82, 0.811, 0.766, 0.446, np.nan, 0.469],
            [
                0.994,
                0.883,
                0.801,
                0.97,
                0.804,
                0.84,
                0.802,
                0.762,
                0.495,
                0.531,
                np.nan,
            ],
        ]
    ),
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
