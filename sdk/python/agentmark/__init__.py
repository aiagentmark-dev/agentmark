"""
agentmark — cryptographic provenance for AI-generated code.

Usage:
    import agentmark

    result = agentmark.call(
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        prompt=prompt,
        challenge_token=challenge,
    )

    manifest = agentmark.sign(
        result=result,
        pipeline_key="my-pipeline-v1",
        private_key=ed25519_private_key_bytes,
    )

    agentmark.verify(manifest, result.raw_bytes)
"""

from agentmark.core import call, sign, verify
from agentmark.challenge import ChallengeRegistry
from agentmark.manifest import Manifest, build_manifest
from agentmark.registry import PipelineRegistry

__version__ = "0.1.0"
__all__ = [
    "call",
    "sign",
    "verify",
    "ChallengeRegistry",
    "Manifest",
    "build_manifest",
    "PipelineRegistry",
]
