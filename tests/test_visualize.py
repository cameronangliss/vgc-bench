"""Tests for vgc_bench.visualize (matrix conversion functions).

We can't directly import visualize.py because it has top-level plotting code
that executes on import. Instead we exec just the function definitions.
"""

import numpy as np


def _load_visualize_functions():
    """Load just the function defs from visualize.py without running the script."""
    from pathlib import Path

    src = Path(__file__).parent.parent / "vgc_bench" / "visualize.py"
    code = src.read_text()
    # Extract only the function definitions + necessary variables
    ns = {"np": np, "plt": None}
    # Execute just the constants and function definitions
    lines = code.splitlines()
    safe_lines = []
    in_func = False
    for line in lines:
        if line.startswith("def "):
            in_func = True
        if line.startswith(("algos =", "titles =")):
            safe_lines.append(line)
            continue
        if in_func:
            safe_lines.append(line)
            if line and not line[0].isspace() and not line.startswith("def "):
                in_func = False
                safe_lines.pop()
    exec("\n".join(safe_lines), ns)
    return ns["matrix_to_latex"], ns["matrix_to_markdown"]


matrix_to_latex, matrix_to_markdown = _load_visualize_functions()


class TestMatrixToLatex:
    def test_basic_output(self):
        matrix = np.array([[0.5, 0.7], [0.3, np.nan]])
        result = matrix_to_latex(matrix, 0)
        assert "\\begin{tabular}" in result
        assert "\\end{tabular}" in result
        assert "0.500" in result
        assert "0.700" in result
        assert "--" in result

    def test_nan_handling(self):
        matrix = np.array([[np.nan]])
        result = matrix_to_latex(matrix, 0)
        assert "--" in result


class TestMatrixToMarkdown:
    def test_basic_output(self):
        matrix = np.array([[0.5, 0.7], [0.3, np.nan]])
        result = matrix_to_markdown(matrix, 0)
        assert "|" in result
        assert "0.5" in result
        assert "--" in result
        assert "1 team" in result

    def test_nan_handling(self):
        matrix = np.array([[np.nan]])
        result = matrix_to_markdown(matrix, 0)
        assert "--" in result
