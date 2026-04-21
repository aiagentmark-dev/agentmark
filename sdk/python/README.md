# agentmark

**Cryptographic provenance for AI-generated code.**

agentmark proves that code traveled through a verified autonomous AI pipeline with no direct human write path — and provides a verifiable audit trail for every commit.

[![spec](https://img.shields.io/badge/spec-v0.1-blue)](https://github.com/aiagentmark-dev/agentmark/blob/main/SPEC.md)
[![license](https://img.shields.io/badge/license-Apache%202.0-green)](https://github.com/aiagentmark-dev/agentmark/blob/main/LICENSE)
[![tests](https://github.com/aiagentmark-dev/agentmark/actions/workflows/tests.yml/badge.svg)](https://github.com/aiagentmark-dev/agentmark/actions/workflows/tests.yml)

## Installation

```bash
pip install agentmark

# With provider support
pip install agentmark[anthropic]
pip install agentmark[openai]
pip install agentmark[all]
```

## What it does

agentmark attaches a cryptographically verifiable manifest to every AI-generated commit:

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
  "signature": "TuBWjzVsxEwy33mS..."
}
```

The manifest proves:
- **output_hash** — committed code matches raw LLM response byte-for-byte
- **challenge_token** — the LLM processed this specific task
- **request_id** — a real API call happened at the declared provider
- **signature** — a registered pipeline identity signed this commit

## Quick start

```python
import agentmark
from agentmark import ChallengeRegistry, PipelineRegistry

# Issue challenge for the task
challenge = ChallengeRegistry().issue("myorg/myrepo#42")

# Call LLM with provenance capture
result = agentmark.call(
    provider="anthropic",
    model="claude-sonnet-4-20250514",
    prompt="Implement a signing function.",
    challenge_token=challenge,
)

# Sign the manifest
manifest = agentmark.sign(
    result=result,
    pipeline_key="my-pipeline-v1",
    private_key_bytes=ed25519_private_key_bytes,
)

# Verify (runs in CI)
result = agentmark.verify(manifest, result.raw_bytes)
```

## Security

Core dependency: [`cryptography`](https://pypi.org/project/cryptography/) >= 46.0.0 (pyca — 82M+ weekly downloads, actively maintained).

agentmark does **not** depend on LiteLLM or any AI gateway proxy. Provider SDKs are optional extras. We call provider APIs directly.

## Links

- [SPEC.md](https://github.com/aiagentmark-dev/agentmark/blob/main/SPEC.md) — full specification
- [API docs](https://github.com/aiagentmark-dev/agentmark/blob/main/docs/API.md)
- [agentmark.dev](https://agentmark.dev)

## License

Apache 2.0
