"""agentmark.verifier — verification algorithm (SPEC.md §8)"""

import hashlib
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentmark.manifest import Manifest
    from agentmark.registry import PipelineRegistry
    from agentmark.core import VerifyResult

REQUEST_ID_PATTERNS = {
    "anthropic": re.compile(r"^req_01[a-zA-Z0-9]{20,}$"),
    "openai":    re.compile(r"^req-[a-f0-9]{20,}$|^[0-9a-f-]{36}$"),
    "google":    re.compile(r"^[0-9a-f-]{36}$"),
    "mistral":   re.compile(r"^[0-9a-f-]{36}$"),
    "local":     None,
}


def run_verification(
    manifest: "Manifest",
    raw_bytes: bytes,
    registry: "PipelineRegistry",
    strict: bool = True,
) -> "VerifyResult":
    from agentmark.core import VerifyResult
    from agentmark.signing import verify_signature
    from agentmark.challenge import ChallengeRegistry

    checks = {}
    failure_reason = None

    # 1. Schema valid
    required = ["version", "provider", "model", "output_hash",
                 "challenge_token", "pipeline_key", "timestamp"]
    missing = [f for f in required if not getattr(manifest, f, None)]
    checks["schema_valid"] = len(missing) == 0
    if missing:
        failure_reason = f"schema_invalid:{missing[0]}"

    # 2. Signature valid
    pub_key = registry.get_public_key(manifest.pipeline_key)
    if pub_key is None:
        checks["signature"] = False
        failure_reason = failure_reason or "unregistered_pipeline_key"
    else:
        sig_valid, sig_reason = verify_signature(
            pub_key, manifest, manifest.signature or ""
        )
        checks["signature"] = sig_valid
        if not sig_valid:
            failure_reason = failure_reason or sig_reason

    # 3. output_hash match
    computed = "sha256:" + hashlib.sha256(raw_bytes).hexdigest()
    checks["output_hash"] = computed == manifest.output_hash
    if not checks["output_hash"]:
        failure_reason = failure_reason or "output_hash_mismatch"

    # 4. Challenge echo present in raw bytes
    echo = f"agentmark-challenge-echo: {manifest.challenge_token}"
    checks["challenge_echo"] = echo.encode() in raw_bytes
    if not checks["challenge_echo"]:
        failure_reason = failure_reason or "challenge_echo_missing"

    # 5. request_id format (Tier 1 only)
    if strict and manifest.provider != "local":
        req_id = manifest.request_id or ""
        pattern = REQUEST_ID_PATTERNS.get(manifest.provider)
        if not req_id:
            checks["request_id"] = False
            failure_reason = failure_reason or "missing_request_id"
        elif pattern and not pattern.match(req_id):
            checks["request_id"] = False
            failure_reason = failure_reason or "request_id_format_mismatch"
        else:
            checks["request_id"] = True
    else:
        checks["request_id"] = True  # not required for local / non-strict

    # 6. direct_provider_call
    checks["direct_provider_call"] = manifest.direct_provider_call is True
    if not checks["direct_provider_call"]:
        failure_reason = failure_reason or "proxy_detected"

    all_pass = all(v for k, v in checks.items() if isinstance(v, bool))

    return VerifyResult(
        valid=all_pass,
        checks=checks,
        failure_reason=failure_reason if not all_pass else None,
    )
