"""agentmark.challenge — single-use challenge token registry"""

import uuid
from datetime import datetime, timezone, timedelta


class ChallengeRegistry:
    """
    In-memory single-use challenge token store.
    In production this would be backed by Redis or a database.
    """

    def __init__(self, ttl_hours: int = 24):
        self._store: dict[str, dict] = {}
        self._ttl = timedelta(hours=ttl_hours)

    def issue(self, task_ref: str) -> str:
        """Issue a new single-use challenge token for a task."""
        token = "agentmark-" + uuid.uuid4().hex[:16]
        self._store[token] = {
            "task_ref": task_ref,
            "used": False,
            "issued_at": datetime.now(timezone.utc),
        }
        return token

    def verify_and_consume(self, token: str) -> tuple[bool, str]:
        """
        Verify a challenge token and mark it as used.
        Returns (valid, reason).
        """
        if token not in self._store:
            return False, "challenge_not_found"

        entry = self._store[token]

        if entry["used"]:
            return False, "challenge_already_used"

        age = datetime.now(timezone.utc) - entry["issued_at"]
        if age > self._ttl:
            return False, "challenge_expired"

        self._store[token]["used"] = True
        return True, "ok"
