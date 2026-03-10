"""Pytest fixtures for API tests."""
import os
import pytest
import httpx

from tests.helpers.api_client import NonogramAPI
from tests.helpers.test_data import matrix_sample, matrix_empty, matrix_small

# Default test user (from setup_db.sql)
DEFAULT_USERNAME = "player1"


# --- HTTP client ---

@pytest.fixture(scope="session")
def api_base_url() -> str:
    """API base URL from env or default."""
    return os.getenv("API_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def http_client(api_base_url: str):
    """Low-level HTTP client."""
    with httpx.Client(base_url=api_base_url, timeout=10.0) as client:
        yield client


@pytest.fixture(scope="session")
def api(http_client: httpx.Client) -> NonogramAPI:
    """API client (Service Object) - encapsulates endpoints."""
    return NonogramAPI(http_client)


@pytest.fixture(scope="session")
def api_client(http_client: httpx.Client) -> httpx.Client:
    """Alias for http_client (backward compatibility)."""
    return http_client


# --- Payload / level builders (factory pattern) ---

def build_send_payload(
    difficulty: str,
    matrix: list,
    label: str = "test-level",
    emoji: str = "🧪",
) -> dict:
    """Factory: payload for POST /api/game/send."""
    return {
        "difficulty": difficulty,
        "matrix": matrix,
        "label": label,
        "emoji": emoji,
    }


# --- Level fixtures (before=send, after=delete) ---

@pytest.fixture
def level_for_load(api: NonogramAPI):
    """Create level via send, yield level info, delete on teardown."""
    data = api.game.send(
        difficulty="easy",
        matrix=matrix_sample(),
        label="load-test-level",
        emoji="🧪",
    )
    level_info = {
        "difficulty": data["difficulty"],
        "level": data["levelNumber"],
        "matrix": data["matrix"],
    }
    yield level_info
    api.game.delete(data["difficulty"], data["levelNumber"])


@pytest.fixture
def level_for_difficulty(api: NonogramAPI, request):
    """
    Create level via send (before), yield level info, delete (after).
    request.param = difficulty (easy/medium/hard).
    """
    difficulty = request.param
    matrix = matrix_small()
    data = api.game.send(
        difficulty=difficulty,
        matrix=matrix,
        label=f"load-diff-test-{difficulty}",
        emoji="🔢",
    )
    yield {"difficulty": data["difficulty"], "level": data["levelNumber"], "matrix": matrix}
    api.game.delete(data["difficulty"], data["levelNumber"])


@pytest.fixture
def level_with_progress(api: NonogramAPI, level_for_load, request):
    """
    Prepare progress state before test. request.param = no_progress | with_progress | empty_progress.
    Yields (level_info, expected_matrix).
    """
    level = level_for_load
    state = request.param

    if state == "with_progress":
        api.progress.save(
            username=DEFAULT_USERNAME,
            level=level["level"],
            difficulty=level["difficulty"],
            matrix=matrix_sample(),
            reason="manual",
        )
        expected = matrix_sample()
    elif state == "empty_progress":
        empty = matrix_empty(7, 7)
        api.progress.save(
            username=DEFAULT_USERNAME,
            level=level["level"],
            difficulty=level["difficulty"],
            matrix=empty,
            reason="manual",
        )
        expected = empty
    else:
        expected = matrix_empty(7, 7)

    yield level, expected
