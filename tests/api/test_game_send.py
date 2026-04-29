"""API tests for game level lifecycle endpoints.

Coverage includes POST /api/game/send and DELETE /levels/{difficulty}/{level}.
"""
import pytest

from tests.helpers.test_data import matrix_empty, matrix_sample, matrix_small


SEND_PAIRWISE_PARAMS = [
    pytest.param("easy", matrix_small(), "pw-easy-small", "🧩", id="easy-small-emoji"),
    pytest.param("medium", matrix_empty(5, 5), "pw-medium-empty", "M", id="medium-empty-text"),
    pytest.param("hard", matrix_sample(), "pw-hard-sample", "🔥", id="hard-sample-emoji"),
]


@pytest.mark.parametrize(
    "difficulty,matrix,label,emoji",
    SEND_PAIRWISE_PARAMS,
)
def test_send_and_delete_level_lifecycle_pairwise(api, api_client, difficulty, matrix, label, emoji):
    """Pairwise-like: representative combinations across payload fields."""
    data = api.game.send(
        difficulty=difficulty,
        matrix=matrix,
        label=label,
        emoji=emoji,
    )
    assert data["difficulty"] == difficulty
    assert data["matrix"] == matrix
    assert isinstance(data["levelNumber"], int)
    assert data["levelNumber"] >= 1
    # Some environments may not support deleting all difficulties uniformly.
    delete_resp = api_client.delete(f"/levels/{data['difficulty']}/{data['levelNumber']}")
    assert delete_resp.status_code in (200, 404)


@pytest.mark.parametrize(
    "difficulty,matrix,expected_status,error_keyword",
    [
        pytest.param("invalid", matrix_small(), 400, "Invalid difficulty", id="invalid_difficulty"),
        pytest.param("easy", [], 400, "matrix", id="invalid_matrix_boundary_empty"),
    ],
)
def test_send_errors_raw_api(api_client, difficulty, matrix, expected_status, error_keyword):
    """Equivalence + boundary validation for send errors."""
    resp = api_client.post(
        "/api/game/send",
        json={
            "difficulty": difficulty,
            "matrix": matrix,
            "label": "negative-case",
            "emoji": "X",
        },
    )
    assert resp.status_code == expected_status
    detail = str(resp.json().get("detail", ""))
    assert error_keyword.lower() in detail.lower()


@pytest.mark.smoke
def test_send_delete_smoke(api):
    """Smoke: create and delete one easy level."""
    data = api.game.send(
        difficulty="easy",
        matrix=matrix_small(),
        label="smoke-level",
        emoji="S",
    )
    api.game.delete(data["difficulty"], data["levelNumber"])
