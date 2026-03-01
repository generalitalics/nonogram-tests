"""API Client: encapsulates endpoints and request structure."""
from typing import Any, Dict, List, Optional
import httpx


class GameAPI:
    """Game/levels API operations."""

    def __init__(self, client: httpx.Client):
        self._client = client

    def send(
        self,
        difficulty: str,
        matrix: List[List[int]],
        label: str = "",
        emoji: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create or update level via POST /api/game/send."""
        payload = {
            "difficulty": difficulty,
            "matrix": matrix,
            "label": label,
            "emoji": emoji,
        }
        resp = self._client.post("/api/game/send", json=payload)
        resp.raise_for_status()
        return resp.json()

    def delete(self, difficulty: str, level_number: int) -> None:
        """Delete level via DELETE /levels/{difficulty}/{level_number}."""
        resp = self._client.delete(f"/levels/{difficulty}/{level_number}")
        resp.raise_for_status()


class ProgressAPI:
    """Progress API operations."""

    def __init__(self, client: httpx.Client):
        self._client = client

    def load(
        self,
        username: str,
        difficulty: str,
        level: int,
    ) -> httpx.Response:
        """Load progress via POST /progress/load."""
        payload = {
            "username": username,
            "difficulty": difficulty,
            "level": level,
        }
        return self._client.post("/progress/load", json=payload)

    def save(
        self,
        username: str,
        level: int,
        difficulty: str,
        matrix: List[List[int]],
        reason: str = "manual",
    ) -> Dict[str, Any]:
        """Save progress via POST /progress/save."""
        payload = {
            "username": username,
            "level": level,
            "difficulty": difficulty,
            "matrix": matrix,
            "reason": reason,
        }
        resp = self._client.post("/progress/save", json=payload)
        resp.raise_for_status()
        return resp.json()


class NonogramAPI:
    """API facade aggregating game and progress operations."""

    def __init__(self, client: httpx.Client):
        self.game = GameAPI(client)
        self.progress = ProgressAPI(client)
