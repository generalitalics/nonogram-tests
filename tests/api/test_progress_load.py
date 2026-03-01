"""API tests for POST /progress/load endpoint.

Test design: pairwise and equivalence partitioning.
Uses: API Client, Object Mother, assertion helpers, indirect fixtures.
"""
import pytest

from tests.helpers.assertions import assert_load_success, assert_load_error
from tests.helpers.test_data import matrix_empty
from conftest import DEFAULT_USERNAME


# --- Error cases ---

LOAD_ERROR_PARAMS = [
    pytest.param(
        "nonexistent_user_xyz",
        "easy",
        1,
        404,
        "not found",
        id="user_not_found",
    ),
    pytest.param(
        DEFAULT_USERNAME,
        "easy",
        99999,
        404,
        "not found",
        id="level_not_found",
    ),
    pytest.param(
        DEFAULT_USERNAME,
        "easy",
        0,
        404,
        "must be >= 1",
        id="invalid_level_zero",
    ),
    pytest.param(
        DEFAULT_USERNAME,
        "invalid_difficulty",
        1,
        404,
        "Invalid difficulty",
        id="invalid_difficulty",
    ),
]


# --- Success: progress state via indirect fixture ---

@pytest.mark.parametrize(
    "level_with_progress",
    ["no_progress", "with_progress", "empty_progress"],
    indirect=True,
    ids=["no_progress", "with_progress", "empty_progress"],
)
class TestLoadProgressSuccess:
    """Success scenarios: 200 OK with correct matrix and compared_matrix."""

    def test_load_returns_200_and_valid_structure(
        self, api, level_with_progress
    ):
        """Load returns 200, has_progress, matrix, compared_matrix, clues."""
        level_info, expected_matrix = level_with_progress
        resp = api.progress.load(
            username=DEFAULT_USERNAME,
            difficulty=level_info["difficulty"],
            level=level_info["level"],
        )
        assert_load_success(
            resp,
            expected_matrix=expected_matrix,
            solution_matrix=level_info["matrix"],
        )


# --- Error cases ---

@pytest.mark.parametrize(
    "username,difficulty,level,expected_status,error_keyword",
    LOAD_ERROR_PARAMS,
)
def test_load_errors(
    api, username, difficulty, level, expected_status, error_keyword
):
    """Load returns 404 for invalid user, level, difficulty."""
    resp = api.progress.load(username=username, difficulty=difficulty, level=level)
    assert_load_error(
        resp,
        expected_status=expected_status,
        error_keyword=error_keyword,
    )


# --- Pairwise: difficulties ---

@pytest.mark.parametrize(
    "level_for_difficulty",
    ["easy", "medium", "hard"],
    indirect=True,
    ids=["easy", "medium", "hard"],
)
def test_load_success_across_difficulties(api, level_for_difficulty):
    """Pairwise: verify load works for each difficulty."""
    level_info = level_for_difficulty
    resp = api.progress.load(
        username=DEFAULT_USERNAME,
        difficulty=level_info["difficulty"],
        level=level_info["level"],
    )
    assert_load_success(
        resp,
        expected_matrix=matrix_empty(3, 3),
        solution_matrix=level_info["matrix"],
    )
