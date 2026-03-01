"""Object Mother / TestData: test data generators."""
from typing import List


def matrix_sample(rows: int = 7, cols: int = 7) -> List[List[int]]:
    """Sample nonogram matrix (flag pattern)."""
    return [
        [1, 1, 1, 1, 1, 1, 1],
        [0, 0, 1, 1, 1, 0, 0],
        [0, 0, 1, 1, 1, 0, 0],
        [0, 0, 1, 1, 1, 0, 0],
        [0, 0, 1, 1, 1, 0, 0],
        [0, 0, 1, 1, 1, 0, 0],
        [1, 1, 1, 1, 1, 1, 1],
    ]


def matrix_empty(rows: int = 7, cols: int = 7) -> List[List[int]]:
    """Empty matrix (all zeros)."""
    return [[0] * cols for _ in range(rows)]


def matrix_small() -> List[List[int]]:
    """Small 3x3 matrix for cross-difficulty tests."""
    return [[1, 0, 1], [0, 1, 0], [1, 0, 1]]
