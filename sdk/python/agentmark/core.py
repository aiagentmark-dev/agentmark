"""
agentmark.core — main entry points: call(), sign(), verify()
"""

from __future__ import annotations
import hashlib
import json
import base64
from dataclasses import dataclass, field
from typing import Optional

from agentmark.providers import get_provider
from agentmark.manifest import Manifest, build_manifest
from agentmark.registry import PipelineRegistry


@dataclass
class CallResult:
    """Result of an agentmark-wrapped LLM API call."""
    raw_bytes: bytes           # full HTTP response body — used for output_hash
    request_id: Optional[str]  # provider-issued request identifier (None for local)
    code: str                  # extracted generated code / text
    provider: str              # e.g. "anthropic", "openai", "local"
    model: str                 # pinned model identifier
    challenge_token: str       # challenge token that was embedded in the prompt
    challenge_echo_verified: bool  # True if echo found in raw_bytes

    @property
    def output_hash(self) -> str:
        return "sha256:" + hashlib.sha256(self.raw_bytes).hexdigest()


def call(
    provider: str,
    model: str,
    prompt: str,
    challenge_token: str,
    **kwargs,
) -> CallResult:
    """
    Make an LLM API call with agentmark provenance capture.

    Wraps the provider SDK call to:
    - Capture raw HTTP response bytes (for output_hash)
    - Extract provider request_id from response headers
    - Verify challenge token echo in response

    Args:
        provider: "anthropic", "openai", "google", "mistral", "local"
        model: Pinned model identifier
        prompt: Prompt text (challenge_token will be appended if not present)
        challenge_token: agentmark challenge token for this task
        **kwargs: Additional kwargs passed to the provider SDK

    Returns:
        CallResult with raw_bytes, request_id, code, and challenge verification
    """
    # Embed challenge if not already in prompt
    if challenge_token not in prompt:
        prompt = _embed_challenge(prompt, challenge_token)

    provider_impl = get_provider(provider)
    return provider_impl.call(
        model=model,
        prompt=prompt,
        challenge_token=challenge_token,
        **kwargs,
    )


def sign(
    result: CallResult,
    pipeline_key: str,
    private_key_bytes: bytes,
    prompt_log_path: Optional[str] = None,
) -> Manifest:
    """
    Build and sign an agentmark manifest from a CallResult.

    Args:
        result: CallResult from agentmark.call()
        pipeline_key: Registered pipeline identifier
        private_key_bytes: Ed25519 private key bytes (DER format)
        prompt_log_path: Optional path to logged prompt/response JSON

    Returns:
        Signed Manifest ready for inclusion in commit message
    """
    from agentmark.signing import sign_manifest

    manifest = build_manifest(
        result=result,
        pipeline_key=pipeline_key,
        prompt_log_path=prompt_log_path,
    )
    manifest.signature = sign_manifest(private_key_bytes, manifest)
    return manifest


def verify(
    manifest: Manifest,
    raw_bytes: bytes,
    registry: Optional[PipelineRegistry] = None,
    strict: bool = True,
) -> VerifyResult:
    """
    Verify an agentmark manifest against committed bytes.

    Runs all checks defined in SPEC.md §8.

    Args:
        manifest: Manifest parsed from commit message
        raw_bytes: Raw HTTP response bytes (from output_hash source)
        registry: Pipeline registry (uses default registry URL if None)
        strict: If True, require request_id for Tier 1 providers

    Returns:
        VerifyResult with valid flag and per-check results
    """
    from agentmark.verifier import run_verification

    if registry is None:
        registry = PipelineRegistry()

    return run_verification(
        manifest=manifest,
        raw_bytes=raw_bytes,
        registry=registry,
        strict=strict,
    )


def _embed_challenge(prompt: str, challenge_token: str) -> str:
    """Append challenge embedding to prompt."""
    return (
        prompt.rstrip()
        + f"\n\n<!-- agentmark-challenge: {challenge_token} -->"
        + f"\n\nYour response MUST contain this exact string on its own line:\n"
        + f"agentmark-challenge-echo: {challenge_token}"
    )


@dataclass
class VerifyResult:
    """Result of agentmark.verify()."""
    valid: bool
    checks: dict
    failure_reason: Optional[str] = None

    def __str__(self) -> str:
        status = "VERIFIED" if self.valid else f"REJECTED ({self.failure_reason})"
        lines = [f"agentmark: {status}"]
        for check, passed in self.checks.items():
            if isinstance(passed, bool):
                mark = "✓" if passed else "✗"
                lines.append(f"  {mark} {check}")
        return "\n".join(lines)
