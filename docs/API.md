# agentmark Python SDK — API Reference

## Installation

```bash
pip install agentmark

# With provider support
pip install agentmark[anthropic]   # Anthropic Claude
pip install agentmark[openai]      # OpenAI GPT
pip install agentmark[all]         # All providers
```

---

## Quick start

```python
import agentmark

# 1. Issue a challenge token for the task
challenge = ChallengeRegistry().issue("myorg/myrepo#42")

# 2. Call the LLM with provenance capture
result = agentmark.call(
    provider="anthropic",
    model="claude-sonnet-4-20250514",
    prompt="Implement a signing function.",
    challenge_token=challenge,
)

# 3. Sign the manifest
manifest = agentmark.sign(
    result=result,
    pipeline_key="my-pipeline-v1",
    private_key_bytes=ed25519_private_key_bytes,
)

# 4. Verify (runs in CI)
result = agentmark.verify(manifest, result.raw_bytes)
print(result)  # agentmark: VERIFIED
```

---

## `agentmark.call()`

Make an LLM API call with agentmark provenance capture.

```python
agentmark.call(
    provider: str,
    model: str,
    prompt: str,
    challenge_token: str,
    **kwargs
) -> CallResult
```

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `provider` | str | Yes | `"anthropic"`, `"openai"`, or `"local"` |
| `model` | str | Yes | Pinned model identifier |
| `prompt` | str | Yes | Prompt text. Challenge token appended automatically if not present |
| `challenge_token` | str | Yes | Single-use token from `ChallengeRegistry.issue()` |
| `**kwargs` | | No | Passed to provider SDK (e.g. `max_tokens`, `temperature`) |

### Returns — `CallResult`

| Attribute | Type | Description |
|---|---|---|
| `raw_bytes` | bytes | Full HTTP response body — source of `output_hash` |
| `request_id` | str \| None | Provider-issued request ID. `None` for local models |
| `code` | str | Extracted generated text/code |
| `provider` | str | Declared provider |
| `model` | str | Model used |
| `challenge_token` | str | Challenge token that was embedded |
| `challenge_echo_verified` | bool | `True` if echo found in raw response |
| `output_hash` | str (property) | `sha256:{hex}` of `raw_bytes` |

### Example

```python
result = agentmark.call(
    provider="openai",
    model="gpt-4o-2024-08-06",
    prompt="Write a Python function that adds two integers.",
    challenge_token="agentmark-3f9a2b1c4d5e6f7a",
    temperature=0,
)

print(result.request_id)    # req-7f3a9b2c...
print(result.output_hash)   # sha256:a1b2c3d4...
print(result.challenge_echo_verified)  # True
```

---

## `agentmark.sign()`

Build and sign an agentmark manifest from a `CallResult`.

```python
agentmark.sign(
    result: CallResult,
    pipeline_key: str,
    private_key_bytes: bytes,
    prompt_log_path: str | None = None,
) -> Manifest
```

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `result` | CallResult | Yes | Output of `agentmark.call()` |
| `pipeline_key` | str | Yes | Registered pipeline identifier |
| `private_key_bytes` | bytes | Yes | Ed25519 private key in DER format |
| `prompt_log_path` | str | No | Path to logged prompt/response JSON |

### Returns — `Manifest`

| Attribute | Type | Description |
|---|---|---|
| `version` | str | Spec version (`"1.0"`) |
| `provider` | str | LLM provider |
| `model` | str | Model identifier |
| `request_id` | str \| None | Provider request ID |
| `output_hash` | str | `sha256:{hex}` of raw response |
| `challenge_token` | str | Challenge token |
| `challenge_echo_verified` | bool | Echo verification result |
| `pipeline_key` | str | Registered pipeline ID |
| `timestamp` | str | ISO 8601 UTC timestamp |
| `signature` | str | Base64 Ed25519 signature |

### Methods

```python
manifest.to_commit_block() -> str
# Returns formatted ```agentmark-manifest ... ``` block for commit message

manifest.to_dict() -> dict
# Returns manifest as dictionary

Manifest.from_commit_message(message: str) -> Manifest
# Parse manifest from a git commit message string
```

### Example

```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding, PrivateFormat, NoEncryption
)

# Generate key (do this once, store securely)
private_key = Ed25519PrivateKey.generate()
private_key_bytes = private_key.private_bytes(
    Encoding.DER, PrivateFormat.PKCS8, NoEncryption()
)

manifest = agentmark.sign(
    result=result,
    pipeline_key="my-pipeline-v1",
    private_key_bytes=private_key_bytes,
)

# Add to commit message
commit_message = f"feat: implement signing (#42)\n\n{manifest.to_commit_block()}"
```

---

## `agentmark.verify()`

Verify an agentmark manifest against committed bytes.

```python
agentmark.verify(
    manifest: Manifest,
    raw_bytes: bytes,
    registry: PipelineRegistry | None = None,
    strict: bool = True,
) -> VerifyResult
```

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `manifest` | Manifest | Yes | Parsed from commit message |
| `raw_bytes` | bytes | Yes | Raw HTTP response bytes |
| `registry` | PipelineRegistry | No | Uses default registry URL if None |
| `strict` | bool | No | Require `request_id` for cloud providers. Default `True` |

### Returns — `VerifyResult`

| Attribute | Type | Description |
|---|---|---|
| `valid` | bool | `True` if all checks pass |
| `checks` | dict | Per-check pass/fail results |
| `failure_reason` | str \| None | First failure reason if `valid=False` |

### Checks performed (SPEC.md §8)

| Check | Failure reason |
|---|---|
| Schema valid | `schema_invalid:{field}` |
| Signature valid | `unregistered_pipeline_key` \| `invalid_signature` |
| output_hash match | `output_hash_mismatch` |
| Challenge echo present | `challenge_echo_missing` |
| request_id format (strict, cloud) | `missing_request_id` \| `request_id_format_mismatch` |
| Direct provider call | `proxy_detected` |

### Example

```python
result = agentmark.verify(manifest, raw_bytes, strict=True)

if result.valid:
    print("VERIFIED — safe to merge")
else:
    print(f"REJECTED — {result.failure_reason}")

# Detailed check output
print(result)
# agentmark: VERIFIED
#   ✓ schema_valid
#   ✓ signature
#   ✓ output_hash
#   ✓ challenge_echo
#   ✓ request_id
#   ✓ direct_provider_call
```

---

## `ChallengeRegistry`

Single-use challenge token store.

```python
from agentmark import ChallengeRegistry

registry = ChallengeRegistry(ttl_hours=24)  # default TTL: 24 hours
```

### Methods

```python
registry.issue(task_ref: str) -> str
# Issue a new challenge token
# task_ref: e.g. "myorg/myrepo#42"
# Returns: "agentmark-{16 hex chars}"

registry.verify_and_consume(token: str) -> tuple[bool, str]
# Verify and mark token as used (single-use)
# Returns: (valid, reason)
# Reasons: "ok" | "challenge_not_found" | "challenge_already_used" | "challenge_expired"
```

---

## `PipelineRegistry`

Pipeline signing key registry.

```python
from agentmark import PipelineRegistry

registry = PipelineRegistry(registry_url="https://registry.agentmark.dev")
```

### Methods

```python
registry.register_local(pipeline_id: str, public_key_bytes: bytes)
# Register a key locally (for testing)

registry.get_public_key(pipeline_id: str) -> bytes | None
# Fetch public key bytes for a pipeline ID

registry.is_registered(pipeline_id: str) -> bool
# Check if a pipeline is registered
```

---

## CLI

```bash
# Verify last commit
agentmark verify

# Verify a commit range
agentmark verify --commits abc123..def456

# Non-strict (allows local models without request_id)
agentmark verify --no-strict

# Write JSON report
agentmark verify --output agentmark-report.json

# Inspect manifest in a commit
agentmark inspect abc123

# Issue a challenge token
agentmark challenge --task "myorg/myrepo#42"
```

---

## Trust tiers

| Tier | Provider | Required fields | Use case |
|---|---|---|---|
| Tier 1 | Cloud (Anthropic, OpenAI, Google) | All fields including `request_id` | External contributors |
| Tier 2 | Local (Ollama, llama.cpp) | All fields except `request_id` | Trusted operators |
| Tier 3 | TEE-attested | All + hardware attestation | v3.0 roadmap |

Use `strict=False` in `agentmark.verify()` to allow Tier 2.

---

## Generating an Ed25519 keypair

```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding, PublicFormat, PrivateFormat, NoEncryption
)

# Generate
private_key = Ed25519PrivateKey.generate()

# Export private key (store in secrets manager)
private_key_bytes = private_key.private_bytes(
    Encoding.DER, PrivateFormat.PKCS8, NoEncryption()
)

# Export public key (register with agentmark registry)
public_key_bytes = private_key.public_key().public_bytes(
    Encoding.DER, PublicFormat.SubjectPublicKeyInfo
)
```

---

## Provider setup

### Anthropic

```bash
pip install agentmark[anthropic]
export ANTHROPIC_API_KEY="sk-ant-..."
```

```python
result = agentmark.call(
    provider="anthropic",
    model="claude-sonnet-4-20250514",
    prompt=prompt,
    challenge_token=challenge,
    max_tokens=8192,
)
```

### OpenAI

```bash
pip install agentmark[openai]
export OPENAI_API_KEY="sk-..."
```

```python
result = agentmark.call(
    provider="openai",
    model="gpt-4o-2024-08-06",
    prompt=prompt,
    challenge_token=challenge,
    temperature=0,
)
```

### Local (Ollama)

```bash
ollama serve
ollama pull llama3
```

```python
result = agentmark.call(
    provider="local",
    model="llama3",
    prompt=prompt,
    challenge_token=challenge,
    base_url="http://localhost:11434",
)
```

Note: local models qualify for Tier 2 only. Use `agentmark.verify(..., strict=False)`.

---

*Full specification: [SPEC.md](SPEC.md) · [agentmark.dev](https://agentmark.dev)*
