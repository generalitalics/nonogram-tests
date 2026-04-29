"""API tests for POST /progress/save endpoint.

Patterns used to minimize cases:
- equivalence partitioning
- boundary value analysis
- pairwise-like representative combinations
"""
import pytest

from conftest import DEFAULT_USERNAME
from tests.helpers.test_data import matrix_empty, matrix_sample


SAVE_ERROR_PARAMS = [
    pytest.param(
        "unknown_user_123",
        "easy",
        1,
        matrix_empty(7, 7),
        404,
        "not found",
        id="user_not_found",
    ),
    pytest.param(
        DEFAULT_USERNAME,
        "invalid_difficulty",
        1,
        matrix_empty(7, 7),
        400,
        "Invalid difficulty",
        id="invalid_difficulty",
    ),
    pytest.param(
        DEFAULT_USERNAME,
        "easy",
        0,
        matrix_empty(7, 7),
        404,
        "not found",
        id="invalid_level_boundary_zero",
    ),
]


@pytest.mark.parametrize(
    "state_matrix,reason",
    [
        pytest.param(matrix_empty(7, 7), "manual", id="empty_progress_manual"),
        pytest.param(matrix_sample(), "manual", id="filled_progress_manual"),
    ],
)
def test_save_success_and_then_load_returns_same_matrix(
    api,
    level_for_load,
    state_matrix,
    reason,
):
    """Pairwise-like: matrix state x reason on valid level/user."""
    saved = api.progress.save(
        username=DEFAULT_USERNAME,
        level=level_for_load["level"],
        difficulty=level_for_load["difficulty"],
        matrix=state_matrix,
        reason=reason,
    )
    assert saved.get("success") is True

    loaded = api.progress.load(
        username=DEFAULT_USERNAME,
        difficulty=level_for_load["difficulty"],
        level=level_for_load["level"],
    )
    assert loaded.status_code == 200
    loaded_matrix = loaded.json()["matrix"]
    assert isinstance(loaded_matrix, list)
    assert len(loaded_matrix) == len(state_matrix)
    assert all(isinstance(row, list) for row in loaded_matrix)


@pytest.mark.parametrize(
    "username,difficulty,level,matrix,expected_status,error_keyword",
    SAVE_ERROR_PARAMS,
)
def test_save_errors_raw_api(
    api_client,
    username,
    difficulty,
    level,
    matrix,
    expected_status,
    error_keyword,
):
    """Equivalence + boundary checks for invalid save inputs."""
    resp = api_client.post(
        "/progress/save",
        json={
            "username": username,
            "difficulty": difficulty,
            "level": level,
            "matrix": matrix,
            "reason": "manual",
        },
    )
    assert resp.status_code == expected_status
    detail = str(resp.json().get("detail", ""))
    assert error_keyword.lower() in detail.lower()


def test_save_error_for_unsupported_reason(api_client, level_for_load):
    """Boundary/business rule: unsupported reason returns 400."""
    resp = api_client.post(
        "/progress/save",
        json={
            "username": DEFAULT_USERNAME,
            "difficulty": level_for_load["difficulty"],
            "level": level_for_load["level"],
            "matrix": matrix_sample(),
            "reason": "autosave",
        },
    )
    assert resp.status_code == 400


@pytest.mark.smoke
def test_save_smoke(api, level_for_load):
    """Smoke: save basic empty matrix for existing user/level."""
    resp = api.progress.save(
        username=DEFAULT_USERNAME,
        level=level_for_load["level"],
        difficulty=level_for_load["difficulty"],
        matrix=matrix_empty(7, 7),
        reason="manual",
    )
    assert resp.get("success") is True
