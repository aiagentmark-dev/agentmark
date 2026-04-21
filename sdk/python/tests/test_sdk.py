"""
agentmark SDK test suite

Tests the full verification stack without needing a real LLM API key.
Uses the same test primitives validated in test_3_signing.py / test_4_end_to_end.py.

Run:
  pip install agentmark[dev]
  pytest tests/ -v
"""

import json
import uuid
import hashlib
import base64
import pytest
from datetime import datetime, timezone, timedelta


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def ed25519_keypair():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding, PublicFormat, PrivateFormat, NoEncryption
    )
    private = Ed25519PrivateKey.generate()
    pub_bytes = private.public_key().public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
    priv_bytes = private.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption())
    return priv_bytes, pub_bytes


@pytest.fixture
def registry(ed25519_keypair):
    from agentmark.registry import PipelineRegistry
    _, pub_bytes = ed25519_keypair
    reg = PipelineRegistry()
    reg.register_local("test-pipeline-v1", pub_bytes)
    return reg


@pytest.fixture
def challenge_registry():
    from agentmark.challenge import ChallengeRegistry
    return ChallengeRegistry()


@pytest.fixture
def valid_raw_bytes(challenge_registry):
    """Simulated raw LLM response bytes with challenge echo."""
    challenge = challenge_registry.issue("test-repo#1")
    raw = json.dumps({
        "id": "msg_01test",
        "type": "message",
        "content": [{
            "type": "text",
            "text": f"def add(a, b):\n    return a + b\n\nagentmark-challenge-echo: {challenge}\n"
        }],
        "model": "claude-sonnet-4-20250514",
        "usage": {"input_tokens": 50, "output_tokens": 30}
    }).encode()
    return challenge, raw


@pytest.fixture
def valid_manifest(ed25519_keypair, valid_raw_bytes):
    from agentmark.manifest import Manifest
    from agentmark.signing import sign_manifest

    priv_bytes, _ = ed25519_keypair
    challenge, raw_bytes = valid_raw_bytes

    manifest = Manifest(
        version="1.0",
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        request_id="req_01abc123def456xyz789",
        output_hash="sha256:" + hashlib.sha256(raw_bytes).hexdigest(),
        challenge_token=challenge,
        challenge_echo_verified=True,
        pipeline_key="test-pipeline-v1",
        direct_provider_call=True,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    manifest.signature = sign_manifest(priv_bytes, manifest)
    return manifest, raw_bytes


# ── manifest tests ────────────────────────────────────────────────────────────

class TestManifest:
    def test_canonical_json_is_deterministic(self, valid_manifest):
        manifest, _ = valid_manifest
        assert manifest.canonical_json() == manifest.canonical_json()

    def test_canonical_json_excludes_signature(self, valid_manifest):
        manifest, _ = valid_manifest
        data = json.loads(manifest.canonical_json())
        assert "signature" not in data

    def test_canonical_json_sorted_keys(self, valid_manifest):
        manifest, _ = valid_manifest
        data = json.loads(manifest.canonical_json())
        assert list(data.keys()) == sorted(data.keys())

    def test_round_trip_commit_block(self, valid_manifest):
        from agentmark.manifest import Manifest
        manifest, _ = valid_manifest
        block = manifest.to_commit_block()
        assert "```agentmark-manifest" in block
        recovered = Manifest.from_commit_message(f"feat: something\n\n{block}")
        assert recovered.output_hash == manifest.output_hash
        assert recovered.challenge_token == manifest.challenge_token
        assert recovered.pipeline_key == manifest.pipeline_key

    def test_from_commit_message_raises_on_missing_block(self):
        from agentmark.manifest import Manifest
        with pytest.raises(ValueError, match="No agentmark-manifest block"):
            Manifest.from_commit_message("feat: normal human commit")


# ── challenge tests ───────────────────────────────────────────────────────────

class TestChallenge:
    def test_issue_returns_token(self, challenge_registry):
        token = challenge_registry.issue("repo#1")
        assert token.startswith("agentmark-")
        assert len(token) == len("agentmark-") + 16

    def test_verify_and_consume_valid(self, challenge_registry):
        token = challenge_registry.issue("repo#1")
        valid, reason = challenge_registry.verify_and_consume(token)
        assert valid
        assert reason == "ok"

    def test_replay_rejected(self, challenge_registry):
        token = challenge_registry.issue("repo#1")
        challenge_registry.verify_and_consume(token)
        valid, reason = challenge_registry.verify_and_consume(token)
        assert not valid
        assert reason == "challenge_already_used"

    def test_fake_token_rejected(self, challenge_registry):
        valid, reason = challenge_registry.verify_and_consume("agentmark-notissued123456")
        assert not valid
        assert reason == "challenge_not_found"


# ── signing tests ─────────────────────────────────────────────────────────────

class TestSigning:
    def test_sign_and_verify(self, ed25519_keypair, valid_manifest):
        from agentmark.signing import verify_signature
        priv_bytes, pub_bytes = ed25519_keypair
        manifest, _ = valid_manifest
        valid, reason = verify_signature(pub_bytes, manifest, manifest.signature)
        assert valid
        assert reason == "ok"

    def test_tampered_manifest_rejected(self, ed25519_keypair, valid_manifest):
        from agentmark.manifest import Manifest
        from agentmark.signing import verify_signature
        priv_bytes, pub_bytes = ed25519_keypair
        manifest, _ = valid_manifest
        tampered = Manifest(**{**manifest.to_dict(),
                               "output_hash": "sha256:tampered000"})
        valid, reason = verify_signature(pub_bytes, tampered, manifest.signature)
        assert not valid
        assert reason == "invalid_signature"

    def test_wrong_key_rejected(self, valid_manifest):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        from agentmark.signing import verify_signature
        manifest, _ = valid_manifest
        rogue_pub = Ed25519PrivateKey.generate().public_key().public_bytes(
            Encoding.DER, PublicFormat.SubjectPublicKeyInfo
        )
        valid, reason = verify_signature(rogue_pub, manifest, manifest.signature)
        assert not valid


# ── verifier tests ────────────────────────────────────────────────────────────

class TestVerifier:
    def test_happy_path(self, valid_manifest, registry):
        from agentmark.verifier import run_verification

        manifest, raw_bytes = valid_manifest
        result = run_verification(manifest, raw_bytes, registry, strict=True)

        # output_hash, signature, challenge_echo, direct_provider_call
        # all pass with valid fixture — challenge token registry check
        # is advisory in v1.0 (no centralized service yet)
        assert result.checks["output_hash"] is True
        assert result.checks["signature"] is True
        assert result.checks["challenge_echo"] is True
        assert result.checks["direct_provider_call"] is True

    def test_output_hash_mismatch(self, valid_manifest, registry):
        from agentmark.verifier import run_verification
        manifest, raw_bytes = valid_manifest
        tampered = raw_bytes.replace(b"def add", b"def hacked")
        result = run_verification(manifest, tampered, registry, strict=True)
        assert result.checks["output_hash"] is False
        assert not result.valid

    def test_missing_signature(self, valid_manifest, registry):
        from agentmark.manifest import Manifest
        from agentmark.verifier import run_verification
        manifest, raw_bytes = valid_manifest
        no_sig = Manifest(**{**manifest.to_dict(), "signature": None})
        result = run_verification(no_sig, raw_bytes, registry, strict=True)
        assert result.checks["signature"] is False

    def test_unregistered_pipeline(self, valid_manifest):
        from agentmark.registry import PipelineRegistry
        from agentmark.verifier import run_verification
        manifest, raw_bytes = valid_manifest
        empty_registry = PipelineRegistry()
        result = run_verification(manifest, raw_bytes, empty_registry, strict=True)
        assert result.checks["signature"] is False
        assert result.failure_reason == "unregistered_pipeline_key"

    def test_challenge_echo_missing(self, ed25519_keypair, registry):
        from agentmark.manifest import Manifest
        from agentmark.signing import sign_manifest
        from agentmark.verifier import run_verification
        priv_bytes, _ = ed25519_keypair

        # Raw bytes without challenge echo
        raw_bytes = b'{"content": [{"text": "def add(a, b): return a + b"}]}'
        challenge = "agentmark-testtoken1234567"

        manifest = Manifest(
            version="1.0",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            request_id="req_01abc123def456xyz789",
            output_hash="sha256:" + hashlib.sha256(raw_bytes).hexdigest(),
            challenge_token=challenge,
            challenge_echo_verified=False,
            pipeline_key="test-pipeline-v1",
            direct_provider_call=True,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        manifest.signature = sign_manifest(priv_bytes, manifest)

        result = run_verification(manifest, raw_bytes, registry, strict=True)
        assert result.checks["challenge_echo"] is False

    def test_request_id_format_mismatch(self, valid_manifest, registry):
        from agentmark.manifest import Manifest
        from agentmark.signing import sign_manifest
        from agentmark.verifier import run_verification

        manifest, raw_bytes = valid_manifest
        # OpenAI format ID claimed as Anthropic
        bad = Manifest(**{**manifest.to_dict(),
                          "provider": "anthropic",
                          "request_id": "chatcmpl-wrongformat"})
        bad.signature = None
        result = run_verification(bad, raw_bytes, registry, strict=True)
        assert result.checks["request_id"] is False

    def test_local_model_no_request_id_non_strict(self, ed25519_keypair, registry):
        from agentmark.manifest import Manifest
        from agentmark.signing import sign_manifest
        from agentmark.verifier import run_verification

        priv_bytes, _ = ed25519_keypair
        challenge = "agentmark-localtest12345678"
        raw_bytes = json.dumps({
            "response": f"def add(a,b): return a+b\nagentmark-challenge-echo: {challenge}"
        }).encode()

        manifest = Manifest(
            version="1.0",
            provider="local",
            model="llama3",
            request_id=None,
            output_hash="sha256:" + hashlib.sha256(raw_bytes).hexdigest(),
            challenge_token=challenge,
            challenge_echo_verified=True,
            pipeline_key="test-pipeline-v1",
            direct_provider_call=True,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        manifest.signature = sign_manifest(priv_bytes, manifest)

        # Non-strict: local model passes without request_id
        result = run_verification(manifest, raw_bytes, registry, strict=False)
        assert result.checks["request_id"] is True
