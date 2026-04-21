# agentmark Python SDK

Cryptographic provenance for AI-generated code.

[![PyPI](https://img.shields.io/pypi/v/agentmark)](https://pypi.org/project/agentmark)
[![Tests](https://github.com/aiagentmark-dev/agentmark/actions/workflows/test.yml/badge.svg)](https://github.com/aiagentmark-dev/agentmark/actions)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](../../LICENSE)

---

## Installation

```bash
pip install agentmark
```

With provider support:

```bash
pip install agentmark[anthropic]   # Anthropic Claude
pip install agentmark[openai]      # OpenAI GPT
pip install agentmark[all]         # all providers
```

---

## Quick start

```python
import agentmark

# 1. Get a challenge token (issued per task by agentmark GitHub App)
#    For testing, generate one manually:
from agentmark.challenge import ChallengeRegistry
registry = ChallengeRegistry()
challenge = registry.issue("myorg/myrepo#42")

# 2. Call your LLM with provenance capture
result = agentmark.call(
    provider="anthropic",                    # or "openai", "local"
    model="claude-sonnet-4-20250514",
    prompt="Write a function that adds two numbers.",
    challenge_token=challenge,
)

print(result.output_hash)           # sha256:abc123...
print(result.request_id)            # req_011CZRtQ...
print(result.challenge_echo_verified)  # True

# 3. Sign the manifest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding, PrivateFormat, NoEncryption
)
private_key = Ed25519PrivateKey.generate()
private_key_bytes = private_key.private_bytes(
    Encoding.DER, PrivateFormat.PKCS8, NoEncryption()
)

manifest = agentmark.sign(
    result=result,
    pipeline_key="my-pipeline-v1",
    private_key_bytes=private_key_bytes,
)

print(manifest.to_commit_block())
# ```agentmark-manifest
# {
#   "version": "1.0",
#   "provider": "anthropic",
#   ...
# }
# ```

# 4. Verify
from agentmark.registry import PipelineRegistry
from cryptography.hazmat.primitives.serialization import (
    PublicFormat
)

pub_bytes = private_key.public_key().public_bytes(
    Encoding.DER, PublicFormat.SubjectPublicKeyInfo
)
reg = PipelineRegistry()
reg.register_local("my-pipeline-v1", pub_bytes)

result_verify = agentmark.verify(
    manifest=manifest,
    raw_bytes=result.raw_bytes,
    registry=reg,
    strict=False,   # strict=True requires request_id for cloud providers
)

print(result_verify.valid)          # True
print(result_verify)
# agentmark: VERIFIED
#   ✓ schema_valid
#   ✓ signature
#   ✓ output_hash
#   ✓ challenge_echo
#   ✓ request_id
#   ✓ direct_provider_call
```

---

## CLI

```bash
# Verify the last commit in current repo
agentmark verify

# Verify a commit range (e.g. in CI)
agentmark verify --commits abc123..def456 --strict

# Inspect manifest from a specific commit
agentmark inspect abc123

# Issue a challenge token
agentmark challenge --task myorg/myrepo#42
```

---

## Providers

### Anthropic

```python
result = agentmark.call(
    provider="anthropic",
    model="claude-sonnet-4-20250514",
    prompt=prompt,
    challenge_token=challenge,
    max_tokens=4096,
)
# request_id header: "request-id"
```

### OpenAI

```python
result = agentmark.call(
    provider="openai",
    model="gpt-4o-2024-08-06",
    prompt=prompt,
    challenge_token=challenge,
    temperature=0,
)
# request_id header: "x-request-id"
```

### Local (Ollama)

```python
result = agentmark.call(
    provider="local",
    model="llama3",
    prompt=prompt,
    challenge_token=challenge,
    base_url="http://localhost:11434",
)
# request_id: None (Tier 2 trust — use strict=False for verify)
```

---

## Trust tiers

| Tier | Provider | request_id | Verification |
|---|---|---|---|
| 1 | Anthropic, OpenAI, Google, Mistral | Required | Full — all 6 checks |
| 2 | Local (Ollama, llama.cpp) | Not available | output_hash + challenge_echo + signature |

Use `strict=False` for Tier 2:

```python
result = agentmark.verify(manifest, raw_bytes, registry, strict=False)
```

---

## Manifest schema

Every agentmark-verified commit includes this block in the commit message:

```json
{
  "version": "1.0",
  "provider": "anthropic",
  "model": "claude-sonnet-4-20250514",
  "request_id": "req_011CZRtQztYq...",
  "output_hash": "sha256:a1b2c3d4...",
  "challenge_token": "agentmark-3f9a2b1c4d5e6f7a",
  "challenge_echo_verified": true,
  "pipeline_key": "my-pipeline-v1",
  "prompt_log": "logs/run-001.json",
  "direct_provider_call": true,
  "timestamp": "2026-04-17T10:22:47Z",
  "signature": "base64-ed25519-signature..."
}
```

See [SPEC.md](../../SPEC.md) for full field definitions.

---

## GitHub Action (CI gate)

Add to `.github/workflows/agentmark-verify.yml`:

```yaml
name: agentmark verification
on:
  pull_request:
    branches: [main]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install agentmark
      - run: agentmark verify --strict
```

---

## Running tests

```bash
pip install agentmark[dev]
pytest tests/ -v
```

No API key needed — all tests use local cryptographic primitives.

---

## Known limitations

- **output_hash** requires direct provider API calls. LiteLLM, Bedrock, and Azure OpenAI proxies transform responses and break hash verification.
- **request_id** is not available for local models. Use `strict=False`.
- **Challenge token** issuance requires the agentmark GitHub App (in development). For now, use `ChallengeRegistry` directly.

Full list of failure modes in [SPEC.md §4](../../SPEC.md#4-known-failure-modes-and-limitations).

---

## License

Apache 2.0 — see [LICENSE](../../LICENSE).
