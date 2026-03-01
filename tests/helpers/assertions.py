"""Response assertion helpers."""
import base64
import json
from typing import List, Optional

import httpx


def decode_compared_matrix(encoded: str) -> List[List[int]]:
    """Decode base64-encoded JSON matrix from load response."""
    if not encoded:
        return []
    return json.loads(base64.b64decode(encoded).decode("utf-8"))


def assert_load_success(
    response: httpx.Response,
    *,
    expected_matrix: List[List[int]],
    solution_matrix: List[List[int]],
) -> dict:
    """Assert load response is 200 and has valid structure."""
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()

    assert data.get("success") is True
    assert "matrix" in data
    assert "compared_matrix" in data
    assert "rowClues" in data
    assert "colClues" in data
    assert "level_id" in data

    decoded = decode_compared_matrix(data["compared_matrix"])
    assert decoded == solution_matrix
    assert data["matrix"] == expected_matrix

    return data


def assert_load_error(
    response: httpx.Response,
    *,
    expected_status: int = 404,
    error_keyword: Optional[str] = None,
) -> dict:
    """Assert load response is error with expected status."""
    assert response.status_code == expected_status
    data = response.json()
    if error_keyword:
        detail = data.get("detail", "")
        if isinstance(detail, dict):
            detail = str(detail.get("message", detail))
        assert error_keyword.lower() in detail.lower()
    return data
