"""
agentmark.manifest — Manifest dataclass and builder
agentmark.challenge — ChallengeRegistry
agentmark.registry  — PipelineRegistry
agentmark.signing   — Ed25519 signing
agentmark.verifier  — Verification algorithm
"""

# ── manifest ────────────────────────────────────────────────────────────────

from __future__ import annotations
import json
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from agentmark.core import CallResult


@dataclass
class Manifest:
    version: str = "1.0"
    provider: str = ""
    model: str = ""
    request_id: Optional[str] = None
    output_hash: str = ""
    challenge_token: str = ""
    challenge_echo_verified: bool = False
    pipeline_key: str = ""
    prompt_log: Optional[str] = None
    direct_provider_call: bool = True
    timestamp: str = ""
    signature: Optional[str] = None

    def to_dict(self, include_signature: bool = True) -> dict:
        d = {k: v for k, v in asdict(self).items() if v is not None}
        if not include_signature:
            d.pop("signature", None)
        return d

    def canonical_json(self) -> bytes:
        """Canonical JSON for signing — sorted keys, no signature field."""
        d = self.to_dict(include_signature=False)
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()

    def to_commit_block(self) -> str:
        """Format manifest as commit message block."""
        return (
            "```agentmark-manifest\n"
            + json.dumps(self.to_dict(), indent=2)
            + "\n```"
        )

    @classmethod
    def from_commit_message(cls, message: str) -> "Manifest":
        """Parse manifest from commit message."""
        import re
        match = re.search(
            r"```agentmark-manifest\n(.*?)\n```",
            message,
            re.DOTALL,
        )
        if not match:
            raise ValueError("No agentmark-manifest block found in commit message")
        data = json.loads(match.group(1))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def build_manifest(
    result: "CallResult",
    pipeline_key: str,
    prompt_log_path: Optional[str] = None,
) -> Manifest:
    return Manifest(
        version="1.0",
        provider=result.provider,
        model=result.model,
        request_id=result.request_id,
        output_hash=result.output_hash,
        challenge_token=result.challenge_token,
        challenge_echo_verified=result.challenge_echo_verified,
        pipeline_key=pipeline_key,
        prompt_log=prompt_log_path,
        direct_provider_call=True,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
